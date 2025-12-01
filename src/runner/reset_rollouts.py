"""
重置 PREPARING 狀態的 rollouts 回到 queuing 狀態
這樣 workers 就可以重新處理它們
"""

import asyncio
import agentlightning as agl


async def reset_preparing_rollouts():
    """將所有 PREPARING 狀態的 rollouts 重置為 queuing"""
    store = agl.store.LightningStoreClient("http://localhost:45993")
    
    # 查詢所有 PREPARING 狀態的 rollouts
    # 注意：使用 status_in 參數，並傳入列表
    rollouts = await store.query_rollouts(status_in=["preparing"])
    
    print(f"📝 Found {rollouts.total} rollouts in PREPARING status")
    
    if rollouts.total == 0:
        print("✅ No rollouts to reset")
        await store.close()
        return
    
    # 重置每個 rollout
    for rollout in rollouts.items:
        try:
            # 將 rollout 狀態改回 queuing
            await store.update_rollout(
                rollout_id=rollout.rollout_id,
                status="queuing"
            )
            print(f"✅ Reset rollout {rollout.rollout_id} to queuing")
        except Exception as e:
            print(f"❌ Failed to reset {rollout.rollout_id}: {e}")
    
    await store.close()
    print(f"\n🎉 Reset {rollouts.total} rollouts to queuing status")
    print("🚀 Now run: python -m src.aglrunner")


if __name__ == "__main__":
    asyncio.run(reset_preparing_rollouts())

