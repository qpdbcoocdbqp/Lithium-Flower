import asyncio
import sys
import os
from pathlib import Path

# Add the docker directory to sys.path to allow importing agentlightning
# Assuming this script is run from the workspace root or src directory
current_dir = Path(__file__).resolve().parent
workspace_root = current_dir.parent
docker_dir = workspace_root / "docker"
sys.path.append(str(docker_dir))

try:
    from agentlightning.store.client_server import LightningStoreClient
    from agentlightning.types import TaskInput, RolloutConfig, RolloutStatus, Span
except ImportError:
    print("Error: Could not import agentlightning. Please ensure the docker directory is in your Python path.")
    sys.exit(1)

async def main():
    # Connect to the store server (assuming it's running on default port 4747)
    server_address = "http://localhost:45993"
    client = LightningStoreClient(server_address=server_address)
    
    print(f"Connecting to LightningStore at {server_address}...")

    # Check health (implicitly done by requests, but we can try a simple query)
    try:
        # 1. Start a Rollout
        print("\n--- Starting Rollout ---")
        task_input = TaskInput(args={"prompt": "Hello world"})
        rollout = await client.start_rollout(
            input=task_input,
            mode="test",
            metadata={"author": "example_script"}
        )
        print(f"Rollout started: {rollout.rollout_id}")

        # 2. Start an Attempt
        print("\n--- Starting Attempt ---")
        attempt = await client.start_attempt(rollout_id=rollout.rollout_id)
        print(f"Attempt started: {attempt.attempt_id} (Status: {attempt.status})")

        # 3. Add a Span
        print("\n--- Adding Span ---")
        span = Span(
            rollout_id=rollout.rollout_id,
            attempt_id=attempt.attempt_id,
            name="example_span",
            start_time=0.0,
            end_time=1.0,
            metadata={"info": "test span"}
        )
        added_span = await client.add_span(span)
        print(f"Span added: {added_span.span_id}")

        # 4. Update Rollout
        print("\n--- Updating Rollout ---")
        updated_rollout = await client.update_rollout(
            rollout_id=rollout.rollout_id,
            status=RolloutStatus.COMPLETED,
            metadata={"completion_reason": "success"}
        )
        print(f"Rollout updated status: {updated_rollout.status}")

        # 5. Query Rollouts
        print("\n--- Querying Rollouts ---")
        rollouts_page = await client.query_rollouts(limit=5)
        print(f"Found {rollouts_page.total} rollouts.")
        for r in rollouts_page.items:
            print(f"- {r.rollout_id} ({r.status})")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
