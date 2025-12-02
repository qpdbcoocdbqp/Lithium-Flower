import asyncio
import agentlightning as agl
from agentlightning.tracer import AgentOpsTracer
import time


# 1. Create your agent (implement LitAgent)
class MyAgent(agl.LitAgent[dict]):
    def rollout(self, task, resources, rollout):
        # Your agent logic here
        worker_id = rollout.attempt.worker_id
        print(f"Worker-{worker_id} processing rollout: {rollout.rollout_id} | Input: {task}")
        
        # Simulate some work
        time.sleep(1)
        
        return 1.0  # Return reward or spans


async def worker_task(worker_id: int, store: agl.LightningStore, max_rollouts: int = None):
    """
    Initialize and run a single worker.
    
    Args:
        worker_id: Unique identifier for this worker
        store: The LightningStore instance to connect to
        max_rollouts: Maximum number of rollouts to process (None = unlimited)
    """
    print(f"Starting Worker-{worker_id}...")
    
    # Create a tracer for this worker
    tracer = AgentOpsTracer()
    
    # Create the runner
    runner = agl.LitAgentRunner(
        tracer=tracer,
        max_rollouts=max_rollouts,
        poll_interval=2.0,  # Poll every 2 seconds (faster for demo)
        heartbeat_interval=10.0
    )
    
    # Initialize the runner with the agent
    agent = MyAgent()
    runner.init(agent=agent, hooks=[])
    
    # Initialize the worker with store connection
    runner.init_worker(worker_id=worker_id, store=store)
    
    try:
        # Start processing rollouts
        await runner.iter()
    finally:
        # Clean up
        runner.teardown_worker(worker_id)
        print(f"Worker-{worker_id} finished.")

async def main(store: agl.LightningStore, num_workers: int = 2, max_rollouts_per_worker=None):
    """
    Main function that initializes 4 workers concurrently.
    
    """    
    print(f"Initializing {num_workers} workers...")
    print(f"Workers will share rollouts from the store automatically\n")
    
    try:
        # Create tasks for all workers
        tasks = [
            worker_task(worker_id=i, store=store, max_rollouts=max_rollouts_per_worker)
            for i in range(num_workers)
        ]
        
        # Run all workers concurrently
        await asyncio.gather(*tasks)
        
    finally:
        # Clean up the store connection
        await store.close()
        print("All workers completed. Store closed.")


if __name__ == "__main__":
    # Run the main function
    store = agl.store.LightningStoreClient("http://localhost:45993")
    asyncio.run(main(store=store, num_workers=2, max_rollouts_per_worker=None))
