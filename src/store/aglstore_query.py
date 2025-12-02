import asyncio
import agentlightning as agl

if __name__ == "__main__":
    # connect to store
    store = agl.store.LightningStoreClient("http://localhost:45993")
    # show rollouts
    rollouts = asyncio.run(store.query_rollouts())
    print(f"Number of rollouts: {len(rollouts)}")
    print(f"Pick one rollout: {rollouts[0].model_dump_json(indent=2)}")
    rollout_id = rollouts[0].rollout_id

    # show resources
    resources = asyncio.run(store.query_resources())
    print(f"Number of resources: {len(resources)}")
    print(f"Pick one resource: {resources[0].model_dump_json(indent=2)}")
    latest_resource = asyncio.run(store.get_latest_resources())
    print(f"Latest resource: {latest_resource.model_dump_json(indent=2)}")

    # show attempts
    attempts = asyncio.run(store.query_attempts(rollout_id))
    print(f"Rollout_id: {rollout_id} | Number of attempts : {len(attempts)}")
    print(f"Pick one attempt: {attempts[0].model_dump_json(indent=2)}")
    latest_attempt = asyncio.run(store.get_latest_attempt(rollout_id))
    print(f"Latest attempt: {latest_attempt.model_dump_json(indent=2)}")

    # show spans
    spans = asyncio.run(store.query_spans(rollout_id))
    print(f"Rollout_id: {rollout_id} | Number of spans : {len(spans)}")
    print(f"Pick one span: {spans[0].model_dump_json(indent=2)}")

    # show workers
    workers = asyncio.run(store.query_workers())
    print(f"Number of workers: {len(workers)}")
    print(f"Pick one worker: {workers[0].model_dump_json(indent=2)}")
