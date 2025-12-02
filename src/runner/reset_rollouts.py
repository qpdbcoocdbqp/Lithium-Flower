"""
Reset rollouts in the PREPARING state back to the QUEUING state
so that workers can process them again
"""

import asyncio
import agentlightning as agl


async def reset_preparing_rollouts():
    """Reset all rollouts in the PREPARING state to QUEUING"""
    store = agl.store.LightningStoreClient("http://localhost:45993")
    
    # Query all rollouts in the PREPARING state
    # Note: use the status_in parameter and pass a list
    rollouts = await store.query_rollouts(status_in=["preparing"])
    
    print(f"Found {rollouts.total} rollouts in PREPARING status")
    
    if rollouts.total == 0:
        print("No rollouts to reset")
        await store.close()
        return
    
    # Reset each rollout
    for rollout in rollouts.items:
        try:
            # Change the rollout status back to queuing
            await store.update_rollout(
                rollout_id=rollout.rollout_id,
                status="queuing"
            )
            print(f"Reset rollout {rollout.rollout_id} to queuing")
        except Exception as e:
            print(f"Failed to reset {rollout.rollout_id}: {e}")
    
    await store.close()
    print(f"Reset {rollouts.total} rollouts to QUEUING status")
    print("Now run: python -m src.runner.aglrunner")


if __name__ == "__main__":
    asyncio.run(reset_preparing_rollouts())
