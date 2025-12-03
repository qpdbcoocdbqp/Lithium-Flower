# Copyright (c) Microsoft. All rights reserved.

"""This sample code shows how to run a custom algorithm and rollout runner separately.

"""

import argparse
import asyncio
import json
from typing import Optional, Sequence
from openai import AsyncOpenAI
from rich.console import Console
import agentlightning as agl
from agentlightning.store import LightningStore
from agentlightning.types import Dataset
from src.task.optimize import RAGOptimizer


BASE_URL = "http://localhost:9005/v1"
API_KEY = "***"

console = Console()

class ApoRolloutAgent(agl.LitAgent):
    async def rollout_async(self, task: str, resources: agl.NamedResources, rollout: agl.Rollout) -> float:
        prompt_template = resources.get("prompt_template")
        instruction_and_reward = json.loads(resources.get("instruction").template)
        instruction = instruction_and_reward.get("instruction")
        reward = instruction_and_reward.get("reward")

        if not prompt_template:
            console.print(f"\n[bold yellow][ROLLOUT][/bold yellow] No instruction found: {instruction}")
            return reward

        async_openai_client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)
        optim = RAGOptimizer(async_openai_client=async_openai_client,
            critique_model="qwen3-4b", diversity_temperature=0.2
            )

        data = json.loads(task)
        # retrieved_contents = []
        # retrieved_similarities = []
        # for row in data.get("retrieved_result"):
        #     if row.get("id_") == data.get("id"):
        #         continue
        #     retrieved_contents.append(row.get("text"))
        #     retrieved_similarities.append(1 - row.get("_distance"))

        critique_response = await optim.critique(inputs={
                "instruction": instruction,
                "query": data.get("query"),
                "target_content": data.get("target"),
                "target_similarity": data.get("'target_similarity"),
                "retrieved_contents": ",\n".join(["[{ctx}]".format(ctx=ctx.replace("\n", "")) for ctx in data.get("interfered_contents")]),
                "retrieved_similarities": data.get("interfered_similarities")
            })

        rewrite_response = await optim.rewrite(critiques = {
                "instruction": instruction,
                "critique": critique_response.model_dump_json(indent=2)
            })
        
        console.print(f"\n[bold yellow][ROLLOUT][/bold yellow] Rewrite instruct: {rewrite_response}")
        latest_resources_update = await store.get_latest_resources()
        resources_id = latest_resources_update.resources_id

        resources["instruction"] = agl.PromptTemplate(
            template=json.dumps({
                "instruction": instruction,
                "reward": data.get("reward"),
                "rewrite_instruction": rewrite_response.improved_instruction
                }),
            engine="f-string"
            )
        updated_resources = await store.update_resources(resources_id=resources_id, resources=resources)
        console.print(f"\n[bold yellow][ROLLOUT][/bold yellow] Update instruct: {updated_resources}")
        console.print(f"\n[bold yellow][ROLLOUT][/bold yellow] Reward: {10.0}")
        return 10.0

async def initialize_worker(worker_id: int, store: agl.LightningStore, max_rollouts: int = None):
    """
    Initialize and run a single worker.
    
    Args:
        worker_id: Unique identifier for this worker
        store: The LightningStore instance to connect to
        max_rollouts: Maximum number of rollouts to process (None = unlimited)
    """
    print(f"🚀 Starting Worker-{worker_id}...")
    
    # Create a tracer for this worker
    tracer = agl.AgentOpsTracer()
    
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
    runner.init_worker(worker_id=worker_id, store=store)
    
    try:
        # Start processing rollouts
        # 這裡會自動從 store 拿取 rollout，不同的 worker 會拿到不同的 rollout
        await runner.iter()
    finally:
        # Clean up
        runner.teardown_worker(worker_id)
        print(f"🏁 Worker-{worker_id} finished.")

async def main(num_workers, store, max_rollouts_per_worker=None):
    try:
        # Create tasks for all workers
        tasks = [
            initialize_worker(worker_id=i, store=store, max_rollouts=max_rollouts_per_worker)
            for i in range(num_workers)
        ]
        
        # Run all workers concurrently
        # 所有 workers 會同時運行，自動從 store 分擔 rollouts
        await asyncio.gather(*tasks)
        
    finally:
        # Clean up the store connection
        await store.close()
        print("\n🎉 All workers completed. Store closed.")

if __name__ == "__main__":
    from agentlightning.store import LightningStoreClient
    store = LightningStoreClient("http://localhost:45993")
    asyncio.run(main(num_workers=2, store=store))
