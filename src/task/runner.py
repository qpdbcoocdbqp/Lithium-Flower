import asyncio
import json
from openai import AsyncOpenAI
from rich.console import Console
from agentlightning import (
    LightningStore,
    LitAgent,
    LitAgentRunner,
    NamedResources,
    OtelTracer,
    Rollout,
    RolloutRawResult,
    Span,
    Tracer
    )

from src.task.optimizer import RAGOptimizer


console = Console()
marker = "[bold red][Agent][/bold red]"

class ApoRolloutAgent(LitAgent):
    def __init__(self):
        super().__init__()
        self.async_openai_client = AsyncOpenAI(
            base_url=os.getenv("MODEL_BASE_URL"),
            api_key=os.getenv("API_KEY")
        )

    async def close(self):
        await self.async_openai_client.close()

    async def rollout_async(self, task: str, resources: NamedResources, rollout: Rollout) -> RolloutRawResult:
        # console.print(f"{marker} Initial Optimizer")
        optim = RAGOptimizer(
            async_openai_client=self.async_openai_client,
            critique_model=os.getenv("MODEL"), 
            diversity_temperature=0.2,
            rollout_id=rollout.rollout_id,
            attempt_id=rollout.attempt.attempt_id
        )
        data = json.loads(task)
        # backward()
        # console.print(f"{marker} {rollout.rollout_id} to Critique")
        critique_response = await optim.critique(inputs={
                "instruction":  data.get("instruction"),
                "query": data.get("query"),
                "target_content": data.get("target"),
                "target_similarity": data.get("'target_similarity"),
                "retrieved_contents": ",\n".join(["[{ctx}]".format(ctx=ctx.replace("\n", "")) for ctx in data.get("retrieved_contents")]),
                "retrieved_similarities": data.get("retrieved_similarities")
            })
        # update()
        # console.print(f"{marker} {rollout.rollout_id} to Rewrite")
        rewrite_response = await optim.rewrite(critiques = {
                "instruction": data.get("instruction"),
                "critique": critique_response.model_dump_json(indent=2)
            })

        # Create result span
        result_span = Span.from_attributes(
            rollout_id=rollout.rollout_id,
            attempt_id=rollout.attempt.attempt_id,
            sequence_id=3,
            name="optimizer.output",
            attributes={
                "critique": critique_response.model_dump_json(),
                "rewrite": rewrite_response.model_dump_json(),
            }
        )
        
        # Return all spans: OpenAI API spans + result span
        all_spans = optim.spans + [result_span]
        console.print(f"{marker} rollout_id: {rollout.rollout_id} Returning {len(all_spans)} spans")
        return all_spans

async def initialize_runner(runner_id: int, store: LightningStore, tracer: Tracer, max_rollouts: int = None):
    """
    Initialize and run a single runner.
    
    Args:
        runner_id: Unique identifier for this runner
        store: The LightningStore instance to connect to
        tracer: Shared tracer instance for all runners
        max_rollouts: Maximum number of rollouts to process (None = unlimited)
    """
    console.print(f"{marker} Starting Runner-{runner_id}...")

    
    # Create the runner
    runner = LitAgentRunner(
        tracer=tracer,
        max_rollouts=max_rollouts,
        poll_interval=2.0,  # Poll every 2 seconds (faster if poll_interval lower)
        heartbeat_interval=10.0
    )
    
    # Initialize the runner with the agent
    agent = ApoRolloutAgent()
    runner.init(agent=agent, hooks=[])
    
    # Initialize the runner with store connection
    # Only initialize tracer for the first runner to avoid TracerProvider override
    if runner_id == 0:
        runner.init_worker(worker_id=runner_id, store=store)
    else:
        # For subsequent Runners, manually set store and runner_id without reinitializing tracer
        runner._store = store
        runner.worker_id = runner_id
        # Manually set tracer's store without reinitializing TracerProvider
        if hasattr(tracer, '_store'):
            tracer._store = store
    
    try:
        # Start processing rollouts
        await runner.iter()
    except asyncio.CancelledError:
        console.print(f"{marker} Runner-{runner_id} was cancelled.")
    except Exception as e:
        console.print(f"{marker} Runner-{runner_id} encountered an error: {e}")
    finally:
        # Clean up
        await agent.close()
        runner.teardown_worker(runner_id)
        console.print(f"{marker} Runner-{runner_id} finished.")

async def main(num_runners, store, max_rollouts_per_runner=None):
    # Create a single shared tracer for all runners
    tracer = OtelTracer()
    
    try:
        # Create tasks for all runners
        tasks = [
            initialize_runner(
                runner_id=i,
                store=store,
                tracer=tracer,
                max_rollouts=max_rollouts_per_runner
                )
            for i in range(num_runners)
        ]
        
        # Run all runners concurrently
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        console.print(f"{marker} Main task cancelled. Shutting down runners...")
        
    finally:
        # Clean up the store connection
        await store.close()
        console.print(f"{marker} All Wunners completed. Store closed.")

if __name__ == "__main__":
    import os
    from agentlightning.store import LightningStoreClient
    from dotenv import load_dotenv
    load_dotenv()

    store = LightningStoreClient(os.getenv("LIGHTNING_STORE_URL"))
    asyncio.run(main(num_runners=int(os.getenv("LIGHTNING_NUM_RUNNER")), store=store))
