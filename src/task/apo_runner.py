import argparse
import asyncio
import json
from typing import Optional, Sequence
from openai import AsyncOpenAI
from rich.console import Console
from opentelemetry import trace
import agentlightning as agl
from agentlightning.store import LightningStore
from agentlightning.types import Dataset
from src.task.optimize import RAGOptimizer


console = Console()

marker = "[bold red][Agent][/bold red]"

class ApoRolloutAgent(agl.LitAgent):
    async def rollout_async(self, task: str, resources: agl.NamedResources, rollout: agl.Rollout) -> agl.RolloutRawResult:
        async_openai_client = AsyncOpenAI(
            base_url=os.getenv("MODEL_BASE_URL"),
            api_key=os.getenv("API_KEY")
            )      
             
        # console.print(f"{marker} Initial Optimizer")
        optim = RAGOptimizer(
            async_openai_client=async_openai_client, 
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
        result_span = agl.Span.from_attributes(
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

async def initialize_worker(worker_id: int, store: agl.LightningStore, tracer: agl.Tracer, max_rollouts: int = None):
    """
    Initialize and run a single worker.
    
    Args:
        worker_id: Unique identifier for this worker
        store: The LightningStore instance to connect to
        tracer: Shared tracer instance for all workers
        max_rollouts: Maximum number of rollouts to process (None = unlimited)
    """
    print(f"🚀 Starting Worker-{worker_id}...")

    
    # Create the runner
    runner = agl.LitAgentRunner(
        tracer=tracer,
        max_rollouts=max_rollouts,
        poll_interval=2.0,  # Poll every 2 seconds (faster for demo)
        heartbeat_interval=10.0
    )
    
    # Initialize the runner with the agent
    agent = ApoRolloutAgent()
    runner.init(agent=agent, hooks=[])
    
    # Initialize the worker with store connection
    # Only initialize tracer for the first worker to avoid TracerProvider override
    if worker_id == 0:
        runner.init_worker(worker_id=worker_id, store=store)
    else:
        # For subsequent workers, manually set store and worker_id without reinitializing tracer
        runner._store = store
        runner.worker_id = worker_id
        # Manually set tracer's store without reinitializing TracerProvider
        if hasattr(tracer, '_store'):
            tracer._store = store
    
    try:
        # Start processing rollouts
        await runner.iter()
    finally:
        # Clean up
        runner.teardown_worker(worker_id)
        print(f"🏁 Worker-{worker_id} finished.")

async def main(num_workers, store, max_rollouts_per_worker=None):
    # Create a single shared tracer for all workers
    # tracer = agl.AgentOpsTracer()
    tracer = agl.OtelTracer()
    
    try:
        # Create tasks for all workers
        tasks = [
            initialize_worker(worker_id=i, store=store, tracer=tracer, max_rollouts=max_rollouts_per_worker)
            for i in range(num_workers)
        ]
        
        # Run all workers concurrently
        await asyncio.gather(*tasks)
        
    finally:
        # Clean up the store connection
        await store.close()
        print("\n🎉 All workers completed. Store closed.")

if __name__ == "__main__":
    import os
    from agentlightning.store import LightningStoreClient
    from dotenv import load_dotenv
    load_dotenv()

    store = LightningStoreClient(os.getenv("LIGHTNING_STORE_URL"))
    asyncio.run(main(num_workers=2, store=store))
