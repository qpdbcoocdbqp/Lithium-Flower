# LightningStoreClient 文檔

`LightningStoreClient` 是一個 HTTP 客戶端，用於與遠端 `LightningStoreServer` 進行通訊。它提供了一個 Python 介面，透過 HTTP 執行各種存儲操作。

## 設定值 (Configuration Settings)

初始化 `LightningStoreClient` 時可以使用以下參數：

*   **`server_address`** (`str`): 要連線的 `LightningStoreServer` 位址 (例如：`http://localhost:8080`)。
*   **`retry_delays`** (`Sequence[float]`): 當發生非應用程式錯誤（如網路問題）時，重試請求的退避延遲時間列表（秒）。預設值：`(1.0, 2.0, 5.0)`。設為空序列可停用重試。
*   **`health_retry_delays`** (`Sequence[float]`): 等待伺服器恢復健康時，`/health` 探測之間的延遲時間（秒）。預設值：`(0.1, 0.2, 0.5)`。設為空序列可停用健康檢查。
*   **`request_timeout`** (`float`): 每個單獨 HTTP 請求的超時時間（秒）。預設值：`30.0`。
*   **`connection_timeout`** (`float`): 建立伺服器連線的超時時間（秒）。預設值：`5.0`。

## 存儲操作函數 (Store Operation Functions)

客戶端提供了以下非同步方法來與存儲進行互動：

### Rollout 操作
*   **`start_rollout(input, mode=None, resources_id=None, config=None, metadata=None)`**: 建立並啟動一個新的 rollout。
*   **`enqueue_rollout(input, mode=None, resources_id=None, config=None, metadata=None)`**: 將一個新的 rollout 加入佇列以進行處理。
*   **`dequeue_rollout(worker_id=None)`**: 為 worker 從佇列中取出一個待處理的 rollout。
*   **`get_rollout_by_id(rollout_id)`**: 根據 ID 檢索 rollout。
*   **`update_rollout(rollout_id, ...)`**: 更新現有 rollout 的欄位 (input, mode, resources_id, status, config, metadata)。
*   **`query_rollouts(...)`**: 根據各種過濾條件（狀態、ID 等）查詢 rollouts，支援分頁和排序。
*   **`wait_for_rollouts(rollout_ids, timeout=None)`**: 等待特定的 rollouts 完成。

### Attempt 操作
*   **`start_attempt(rollout_id)`**: 為給定的 rollout 啟動一個新的 attempt。
*   **`update_attempt(rollout_id, attempt_id, ...)`**: 更新 attempt 的狀態、worker ID、心跳或 metadata。
*   **`get_latest_attempt(rollout_id)`**: 檢索 rollout 的最新 attempt。
*   **`query_attempts(rollout_id, ...)`**: 查詢特定 rollout 的 attempts。

### Resource 操作
*   **`add_resources(resources)`**: 新增一個具名的資源快照 (resource snapshot)。
*   **`update_resources(resources_id, resources)`**: 更新現有的資源快照。
*   **`get_resources_by_id(resources_id)`**: 根據 ID 檢索資源快照。
*   **`get_latest_resources()`**: 檢索最新的資源快照。
*   **`query_resources(...)`**: 查詢資源快照，支援過濾和分頁。

### Worker 操作
*   **`query_workers(...)`**: 根據狀態和 ID 過濾條件查詢 workers。
*   **`get_worker_by_id(worker_id)`**: 根據 ID 檢索 worker。
*   **`update_worker(worker_id, heartbeat_stats=None)`**: 更新 worker 的心跳統計資訊。

### Span/Trace 操作
*   **`add_span(span)`**: 將 trace span 新增到存儲中。
*   **`add_otel_span(rollout_id, attempt_id, readable_span, sequence_id=None)`**: 新增一個 OpenTelemetry span。
*   **`get_next_span_sequence_id(rollout_id, attempt_id)`**: 獲取 attempt 中 spans 的下一個序列 ID。
*   **`query_spans(rollout_id, ...)`**: 查詢與 rollout/attempt 相關聯的 spans。
