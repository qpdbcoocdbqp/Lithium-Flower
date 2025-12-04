# Copyright (c) Microsoft. All rights reserved.

"""This sample code shows how to run a custom algorithm and rollout runner separately.

"""

import asyncio
import agentlightning as agl
import json
import time
import random

from typing import Optional, Sequence
from rich.console import Console
from agentlightning.store import LightningStoreClient
from agentlightning.types import PromptTemplate

from task.utils import Encoder, VectorStore
from task.model import Critique, Rewrite
from task.evaluator import Evaluator

import os
from dotenv import load_dotenv
load_dotenv()

console = Console()

## Load vector store
encoder = Encoder(
    name=os.getenv("EMBED_MODEL"),
    base_url=os.getenv("BASE_URL"),
    api_key=os.getenv("API_KEY"),
    dim=int(os.getenv("EMBED_DIM"))
    )

console.print(f"[bold yellow][LanceDB][/bold yellow] Connect to LanceDB")
vector_store = VectorStore(encoder=encoder, table_name=os.getenv("TABLE_NAME"), uri=os.getenv("LANCEDB_URI"))
datasets = vector_store.to_ragset()
console.print(f"[bold yellow][LanceDB][/bold yellow] Number of datasets: {len(datasets)}")

## Connect to Lightning store
store = LightningStoreClient(os.getenv("LIGHTNING_STORE_URL"))

## initial resources
initial_instruction = "Given a query, retrieval the relevant parameter information from the configuration table."
initial_resources = {
    "prompt_template": PromptTemplate(
        template="Instruct: {instruction}\nQuery: {query}",
        engine="f-string"
        ),
    "instruction": PromptTemplate(
        template=json.dumps({
            "instruction": initial_instruction,
            "reward": 0.0,
        }),
        engine="f-string"
    )
}

resources = asyncio.run(store.add_resources(initial_resources))

## init evaluator
evaluator = Evaluator(
    prompt_template=initial_resources.get("prompt_template"),
    vector_store=vector_store
    )


# with open("./task/data/apo_task.json", "r") as f:
#     apo_task = json.load(f)

instruction = json.loads(resources.resources.get("instruction").template).get("instruction")
# candidate_instructs format: [`span_id`, `updated-instruction`, `origin-reward`, `delta-reward`]

candidate_instructs = [["_", instruction, 0.0, 0.0]]

## submit task
async def submit_task(batched_task, instruction):
    rollout_tasks = []
    rollout_ids = []
    rollout_rewards = []
    for i, task in enumerate(batched_task):
        if not task.query or not task.target:
            continue
        reward, target_similarity, retrieved_result = evaluator.reward(
            instruction=instruction,
            query=task.query,
            target=task.target,
            target_id=task.id
            )
        retrieved_contents, retrieved_similarities = zip(*[[row.get("text"), 1 - row.get("_distance")] for row in retrieved_result if row.get("id_") != task.id])
        apo_task = json.dumps({
            "instruction": instruction,
            "query": task.query,
            "target_content": task.target,
            "target_similarity": target_similarity,
            "retrieved_contents": retrieved_contents,
            "retrieved_similarities": retrieved_similarities,
            })
        # rollout = asyncio.run(store.enqueue_rollout(input=apo_task, mode="train"))
        rollout = await store.enqueue_rollout(input=apo_task, mode="train")
        print(f"Enqueued Task {i}")
        rollout_tasks.append(task)
        rollout_ids.append(rollout.rollout_id)
        rollout_rewards.append(reward)
    return [rollout_tasks, rollout_ids, rollout_rewards]

async def pull_task(queues: list):
    steps = []
    for task, rollout_id, reward,  in queues:
        while True:
            # rollouts = asyncio.run(store.wait_for_rollouts(rollout_ids=[rollout_id], timeout=0.01))
            rollouts = await store.wait_for_rollouts(rollout_ids=[rollout_id], timeout=0.01)
            if len(rollouts) == 0:
                time.sleep(2.5)
            else:
                break
        # skip task if status is not succeeded
        if rollouts[0].status != "succeeded":
            continue
        # optim_span = asyncio.run(store.query_spans(rollout_id=rollouts[0].rollout_id, name="optimizer.output"))
        optim_span = await store.query_spans(rollout_id=rollouts[0].rollout_id, name="optimizer.output")
        optim_critique = Critique.model_validate_json(optim_span[0].attributes.get("critique"))
        optim_rewrite = Rewrite.model_validate_json(optim_span[0].attributes.get("rewrite"))
        updated_reward, updated_target_similarity, updated_retrieved_result = evaluator.reward(
            instruction=optim_rewrite.improved_instruction,
            query=task.query,
            target=task.target,
            target_id=task.id
            )
        # [`span_id`, `updated-instruction`, `origin-reward`, `delta-reward`]
        steps.append([optim_span[0].span_id, optim_rewrite.improved_instruction, reward, updated_reward - reward])
    return steps


batch_size = 2
epoch = 0
# for epoch in range(3):

random.shuffle(datasets)
steps = len(datasets) // batch_size
history_instructs = []
for n_step in range(steps): # n_step = 0
    updated_instructs = []
    for span_id, instruction, origin_reward, _ in candidate_instructs:
        submitted_tasks = asyncio.run(submit_task(datasets[n_step*batch_size: (n_step+1)*batch_size], instruction))
        pull_queues = list(zip(*submitted_tasks))
        reward_tasks = asyncio.run(pull_task(queues=pull_queues))
        updated_reward = np.mean(list(map(lambda x: x[2], reward_tasks)))
        updated_instructs.append([span_id, instruction, updated_reward, 0])
        updated_instructs.extend(reward_tasks)
    history_instructs.extend(updated_instructs)
    sorted_reward_tasks = sorted(history_instructs, key=lambda x: x[3], reverse=True)
    candidate_instructs = sorted_reward_tasks[:2]
    console.print(f"[bold yellow][Candidate Instructions][bold yellow] Step {n_step}: candidate {len(candidate_instructs)}, updated {len(updated_instructs)}, history {len(history_instructs)}")

# pick top 2 best delta rewards

import pyarrow as pa
import pyarrow.compute as pc

history_table = pa.table(dict(zip(["id", "inst", "rw", "drw"], zip(*history_instructs))))
history_table = history_table.append_column("frw", pc.add(history_table.column("rw"), history_table.column("drw")))
reward_table = history_table.group_by(["id"]).aggregate([
    ("rw", "mean"),
    ("drw", "mean"),
    ("frw", "mean"),
    ("id", "count"),
    ("inst", "one")
    ]).sort_by([("frw_mean", "descending")])

epoch_reward = reward_table.filter(pc.greater(pc.field("id_count"), 1)).take([0]).to_pydict()

#　epoch_id = epoch_reward.get("id")[0]

reward_span = agl.Span.from_attributes(
    rollout_id=epoch_id,
    sequence_id=epoch,
    name="agentlightning.reward",
    attributes={
        "reward": epoch_reward.get("frw_mean")[0],
        "instruction": epoch_reward.get("inst_one")[0],
    }
)

# name="agentlightning.reward"
final_reward = agl.find_final_reward(reward_span)



