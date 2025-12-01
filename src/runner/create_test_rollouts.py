"""
測試腳本：展示 4 個 workers 如何分擔 20 個 rollouts

這個腳本會：
1. 創建 20 個測試 rollouts（使用 enqueue_rollout 加入 queue）
2. 啟動 4 個 workers
3. 觀察每個 worker 處理了哪些 rollouts
"""

import asyncio
import agentlightning as agl


async def create_test_rollouts(num_rollouts: int = 20):
    """創建測試用的 rollouts 並加入 queue"""
    store = agl.store.LightningStoreClient("http://localhost:45993")
    
    print(f"📝 Creating {num_rollouts} test rollouts and adding to queue...")
    
    for i in range(num_rollouts):
        # 使用 enqueue_rollout 而不是 start_rollout
        # 這樣會將 rollout 加入 queue，workers 才能處理
        await store.enqueue_rollout(
            input={"prompt": f"Task {i+1}", "task_id": i+1},
            mode="test",
            metadata={"batch": "load_balancing_test"}
        )
        print(f"  ✅ Enqueued Task {i+1}")
    
    await store.close()
    print(f"\n✅ Created and enqueued {num_rollouts} rollouts")
    print(f"🚀 Now run: python -m src.aglrunner")
    print(f"   You will see 4 workers sharing these {num_rollouts} rollouts!\n")


if __name__ == "__main__":
    asyncio.run(create_test_rollouts(20))

