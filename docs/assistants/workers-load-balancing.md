# Workers 分擔 Rollouts 機制說明

## 🎯 如何運作

### 1. **自動負載均衡**
Agent Lightning 的 `LitAgentRunner` 內建了自動負載均衡機制：

```python
# 在 runner.iter() 內部，每個 worker 會：
next_rollout = await store.dequeue_rollout(worker_id=self.get_worker_id())
```

- `dequeue_rollout()` 會從 store 中取出**尚未被處理**的 rollout
- Store 會確保每個 rollout 只被一個 worker 拿到
- 不同的 workers 會拿到不同的 rollouts

### 2. **Worker Claiming 機制**
當 worker 拿到 rollout 後，會立即 claim 它：

```python
await store.update_attempt(
    rollout_id, 
    attempt_id, 
    worker_id=self.get_worker_id()
)
```

這樣其他 workers 就知道這個 rollout 已經被處理了。

### 3. **並行處理**
使用 `asyncio.gather()` 讓所有 workers 同時運行：

```python
tasks = [
    worker_task(worker_id=0, store=store),
    worker_task(worker_id=1, store=store),
    worker_task(worker_id=2, store=store),
    worker_task(worker_id=3, store=store),
]
await asyncio.gather(*tasks)
```

## 📊 測試範例

### 步驟 1: 創建測試 rollouts
```bash
python -m src.create_test_rollouts
```

這會在 store 中創建 20 個測試 rollouts。

### 步驟 2: 啟動 4 個 workers
```bash
python -m src.aglrunner
```

你會看到類似這樣的輸出：
```
🔧 Initializing 4 workers...
📊 Workers will share rollouts from the store automatically

🚀 Starting Worker-0...
🚀 Starting Worker-1...
🚀 Starting Worker-2...
🚀 Starting Worker-3...

✅ Worker-0 processing rollout: ro-xxx | Input: {'prompt': 'Task 1', 'task_id': 1}
✅ Worker-1 processing rollout: ro-yyy | Input: {'prompt': 'Task 2', 'task_id': 2}
✅ Worker-2 processing rollout: ro-zzz | Input: {'prompt': 'Task 3', 'task_id': 3}
✅ Worker-3 processing rollout: ro-aaa | Input: {'prompt': 'Task 4', 'task_id': 4}
...
```

每個 worker 會處理大約 5 個 rollouts (20 ÷ 4 = 5)。

## ⚙️ 配置選項

### 調整 worker 數量
```python
num_workers = 8  # 改成 8 個 workers
```

### 限制每個 worker 處理的 rollouts 數量
```python
max_rollouts_per_worker = 5  # 每個 worker 最多處理 5 個
```

### 調整 polling 間隔
```python
poll_interval=2.0  # 每 2 秒檢查一次是否有新的 rollout
```

## 🔍 監控 Workers

### 查詢 worker 狀態
```python
workers = await store.query_workers()
for worker in workers.items:
    print(f"Worker-{worker.worker_id}: {worker.status}")
```

### 查詢哪個 worker 處理了哪個 rollout
```python
attempts = await store.query_attempts(rollout_id)
for attempt in attempts.items:
    print(f"Attempt {attempt.attempt_id} by Worker-{attempt.worker_id}")
```

## 💡 最佳實踐

1. **Worker 數量**: 通常設定為 CPU 核心數或略多
2. **Polling 間隔**: 根據 rollout 的處理時間調整
   - 快速任務: 1-2 秒
   - 慢速任務: 5-10 秒
3. **Heartbeat**: 確保 heartbeat_interval 小於 store 的 timeout 設定
4. **錯誤處理**: Workers 會自動重試失敗的 rollouts（根據 RolloutConfig）

## 🚀 進階用法

### 使用 multiprocessing 實現真正的並行
如果你的任務是 CPU 密集型的，可以使用 multiprocessing：

```python
from multiprocessing import Process

def run_worker(worker_id):
    asyncio.run(worker_task(worker_id, store))

processes = [
    Process(target=run_worker, args=(i,))
    for i in range(4)
]

for p in processes:
    p.start()

for p in processes:
    p.join()
```

### 動態調整 worker 數量
根據 store 中的 rollout 數量動態調整：

```python
rollouts = await store.query_rollouts(status="preparing")
num_workers = min(rollouts.total, 10)  # 最多 10 個 workers
```
