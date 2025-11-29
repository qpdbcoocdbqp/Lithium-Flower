# LightningStoreClient Documentation

`LightningStoreClient` is an HTTP client that communicates with a remote `LightningStoreServer`. It provides a Python interface to perform various store operations over HTTP.

## Configuration Settings

The `LightningStoreClient` is initialized with the following arguments:

*   **`server_address`** (`str`): The address of the `LightningStoreServer` to connect to (e.g., `http://localhost:8080`).
*   **`retry_delays`** (`Sequence[float]`): A list of backoff delays (in seconds) for retrying requests on non-application failures (e.g., network issues). Default: `(1.0, 2.0, 5.0)`. Set to an empty sequence to disable retries.
*   **`health_retry_delays`** (`Sequence[float]`): Delays (in seconds) between `/health` probes when waiting for the server to become healthy. Default: `(0.1, 0.2, 0.5)`. Set to an empty sequence to disable health checks.
*   **`request_timeout`** (`float`): Timeout (in seconds) for each individual HTTP request. Default: `30.0`.
*   **`connection_timeout`** (`float`): Timeout (in seconds) for establishing a connection to the server. Default: `5.0`.

## Store Operation Functions

The client exposes the following asynchronous methods to interact with the store:

### Rollout Operations
*   **`start_rollout(input, mode=None, resources_id=None, config=None, metadata=None)`**: Creates and starts a new rollout.
*   **`enqueue_rollout(input, mode=None, resources_id=None, config=None, metadata=None)`**: Enqueues a new rollout for processing.
*   **`dequeue_rollout(worker_id=None)`**: Dequeues a pending rollout for a worker to process.
*   **`get_rollout_by_id(rollout_id)`**: Retrieves a rollout by its ID.
*   **`update_rollout(rollout_id, ...)`**: Updates fields of an existing rollout (input, mode, resources_id, status, config, metadata).
*   **`query_rollouts(...)`**: Queries rollouts based on various filters (status, ID, etc.) with pagination and sorting.
*   **`wait_for_rollouts(rollout_ids, timeout=None)`**: Waits for specific rollouts to complete.

### Attempt Operations
*   **`start_attempt(rollout_id)`**: Starts a new attempt for a given rollout.
*   **`update_attempt(rollout_id, attempt_id, ...)`**: Updates an attempt's status, worker ID, heartbeat, or metadata.
*   **`get_latest_attempt(rollout_id)`**: Retrieves the latest attempt for a rollout.
*   **`query_attempts(rollout_id, ...)`**: Queries attempts for a specific rollout.

### Resource Operations
*   **`add_resources(resources)`**: Adds a new named resource snapshot.
*   **`update_resources(resources_id, resources)`**: Updates an existing resource snapshot.
*   **`get_resources_by_id(resources_id)`**: Retrieves a resource snapshot by ID.
*   **`get_latest_resources()`**: Retrieves the latest resource snapshot.
*   **`query_resources(...)`**: Queries resource snapshots with filtering and pagination.

### Worker Operations
*   **`query_workers(...)`**: Queries workers based on status and ID filters.
*   **`get_worker_by_id(worker_id)`**: Retrieves a worker by ID.
*   **`update_worker(worker_id, heartbeat_stats=None)`**: Updates a worker's heartbeat statistics.

### Span/Trace Operations
*   **`add_span(span)`**: Adds a trace span to the store.
*   **`add_otel_span(rollout_id, attempt_id, readable_span, sequence_id=None)`**: Adds an OpenTelemetry span.
*   **`get_next_span_sequence_id(rollout_id, attempt_id)`**: Gets the next sequence ID for spans in an attempt.
*   **`query_spans(rollout_id, ...)`**: Queries spans associated with a rollout/attempt.
