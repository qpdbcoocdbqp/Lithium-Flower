import asyncio
import sys
import os
import uuid
from agentlightning.store.client_server import LightningStoreClient
from agentlightning.types import RolloutConfig, RolloutStatus, Span


def main():

    # Connect to the store server (assuming it's running on default port 4747)
    server_address = "http://localhost:45993"
    client = LightningStoreClient(server_address=server_address)
    
    print(f"Connecting to LightningStore at {server_address}...")

    # Check health (implicitly done by requests, but we can try a simple query)
    try:
        # 1. Start a Rollout
        print("\n--- Starting Rollout ---")
        task_input = {"prompt": "Hello world"}
        rollout = asyncio.run(client.start_rollout(
            input=task_input,
            mode="test",
            metadata={"author": "example_script"}
        ))
        print(f"Rollout started: {rollout.rollout_id}")

        # 2. Start an Attempt
        print("\n--- Starting Attempt ---")
        attempt = asyncio.run(client.start_attempt(rollout_id=rollout.rollout_id))
        # Assuming attempt is the Attempt object directly
        print(f"Attempt started: {attempt.attempt.attempt_id} (Status: {attempt.attempt.status})")

        # 3. Add a Span
        print("\n--- Adding Span ---")
        # Use Span.from_attributes to handle default values for required fields
        span = Span.from_attributes(
            rollout_id=rollout.rollout_id,
            attempt_id=attempt.attempt.attempt_id,
            sequence_id=0,
            name="example_span",
            start_time=0.0,
            end_time=1.0,
            attributes={"info": "test span"}
        )
        added_span = asyncio.run(client.add_span(span))
        print(f"Span added: {added_span.span_id}")

        # 4. Update Rollout
        print("\n--- Updating Rollout ---")
        updated_rollout = asyncio.run(client.update_rollout(
            rollout_id=rollout.rollout_id,
            status="cancelled",
            metadata={"completion_reason": "success"}
        ))
        print(f"Rollout updated status: {updated_rollout.status}")


        # 5. Query Rollouts
        print("\n--- Querying Rollouts ---")
        rollouts_page = asyncio.run(client.query_rollouts(limit=5))
        print(f"Found {rollouts_page.total} rollouts.")
        for r in rollouts_page.items:
            print(f"- {r.rollout_id} ({r.status})")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        asyncio.run(client.close())

if __name__ == "__main__":
    main()
