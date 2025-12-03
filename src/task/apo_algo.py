# Copyright (c) Microsoft. All rights reserved.

"""This sample code shows how to run a custom algorithm and rollout runner separately.

"""

import asyncio
import agentlightning as agl
import json
from typing import Optional, Sequence
from rich.console import Console
from agentlightning.store import LightningStoreClient
from agentlightning import NamedResources
from agentlightning.types import PromptTemplate


console = Console()
async def log_llm_span(spans: Sequence[agl.Span]) -> None:
    """Logs the LLM related spans that records prompts and responses."""
    for span in spans:
        if "chat.completion" in span.name:
            console.print(f"[bold green][LLM][/bold green] Span {span.span_id} ({span.name}): {span.attributes}")

with open("./backup/data/apo_task.json", "r") as f:
    apo_task = json.load(f)


initial_resources: NamedResources = {
    "prompt_template": PromptTemplate(
        template="Instruct: {instruction}\nQuery: {query}",
        engine="f-string"
        ),
    "instruction": PromptTemplate(
        template=json.dumps({
            "instruction": "Given a query, retrieval the relevant parameter information from the configuration table.",
            "reward": 0.0,
        }),
        engine="f-string"
    )
}

resources_resp = asyncio.run(store.add_resources(initial_resources))
store = LightningStoreClient("http://localhost:45993")

rollout = asyncio.run(store.enqueue_rollout(input=json.dumps(apo_task), mode="train"))
console.print(f"Received Result: {rollout.rollout_id}")
console.print(f"Received Result: {rollout.status}")

rollouts = asyncio.run(store.wait_for_rollouts(rollout_ids=[rollout.rollout_id], timeout=0.01))
rollouts[0].status
rollouts[0].rollout_id
spans = asyncio.run(store.query_spans(rollouts[0].rollout_id))

# for span in spans:
#     console.print(span.sequence_id)
# asyncio.run(log_llm_span(spans))
final_reward = agl.find_final_reward(spans)

latest_resources_update = asyncio.run(store.get_latest_resources())
if latest_resources_update:
    current_resources = latest_resources_update.resources
    current_resources["instruction"] = agl.PromptTemplate(
        template=json.dumps({
            "instruction": best_instruction[0],
            "reward": best_instruction[1]
            }),
        engine="f-string"
    )
updated_resources = await store.update_resources(resources_id=resources_id, resources=current_resources)

latest_resources_update = await store.get_latest_resources()
resources_id = latest_resources_update.resources_id