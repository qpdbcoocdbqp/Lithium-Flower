"""
Test script: Demonstrates how 4 workers share 20 rollouts

This script will:
1. Create 20 test rollouts (added to the queue using enqueue_rollout)
2. Start 4 workers
3. Observe which rollouts are handled by each worker
"""

import asyncio
import agentlightning as agl


async def create_test_rollouts(num_rollouts: int = 20):
    """Create test rollouts and add them to the queue"""
    store = agl.store.LightningStoreClient("http://localhost:45993")
    
    print(f"Creating {num_rollouts} test rollouts and adding them to the queue...")
    
    for i in range(num_rollouts):
        # Use enqueue_rollout instead of start_rollout
        # This will add the rollout to the queue so that workers can process it
        await store.enqueue_rollout(
            input={"prompt": f"Task {i+1}", "task_id": i+1},
            mode="test",
            metadata={"batch": "load_balancing_test"}
        )
        print(f"Enqueued Task {i+1}")
    
    await store.close()
    print(f"Created and enqueued {num_rollouts} rollouts")
    print(f"Now run: python -m src.aglrunner")
    print(f"You will see 4 workers sharing these {num_rollouts} rollouts!")


if __name__ == "__main__":
    asyncio.run(create_test_rollouts(20))
