import asyncio
import json
import random
import time
import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
from agentlightning.store import LightningStore
from pydantic import BaseModel
from pyarrow.acero import (
    Declaration,
    TableSourceNodeOptions,
    ProjectNodeOptions,
    AggregateNodeOptions,
    OrderByNodeOptions,
    FilterNodeOptions
    )
from rich.console import Console
from typing import Optional
from src.task.evaluator import Evaluator
from src.task.model import Critique, Rewrite
from src.task.utils import QueryTask


console = Console()

class CandidateInstruction(BaseModel):
    span_id: Optional[str]="root_span"
    instruction: str
    origin_reward: Optional[float]=0.0
    delta_reward: Optional[float]=0.0


class Trainer():
    def __init__(self, store: LightningStore, evaluator: Evaluator, history: list[CandidateInstruction]=None):
        self.marker = "[bold dark_violet][Trainer][/bold dark_violet]"
        self.store = store
        self.evaluator = evaluator
        if history:
            self._history = history
        else:
            self._history= [CandidateInstruction(
                instruction="Given a query, retrieval the relevant parameter information from the configuration table."
            )]
        console.print(f"{self.marker} Trainer is initialized.")
        pass

    async def submit_tasks(self, tasks: list[QueryTask], instruction: str) -> list:
        rollout_tasks = []
        rollout_ids = []
        rollout_rewards = []
        for i, task in enumerate(tasks):
            if not task.query or not task.target:
                continue
            reward, target_similarity, retrieved_result = self.evaluator.reward(
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
            rollout = await self.store.enqueue_rollout(input=apo_task, mode="train")
            console.print(f"{self.marker} Enqueued Task {i}")
            rollout_tasks.append(task)
            rollout_ids.append(rollout.rollout_id)
            rollout_rewards.append(reward)
        return [rollout_tasks, rollout_ids, rollout_rewards]

    async def pull_tasks(self, queues: list) -> list[CandidateInstruction]:
        steps = []
        for task, rollout_id, reward in queues:
            while True:
                # rollouts = asyncio.run(store.wait_for_rollouts(rollout_ids=[rollout_id], timeout=0.01))
                rollouts = await self.store.wait_for_rollouts(rollout_ids=[rollout_id], timeout=0.01)
                if len(rollouts) == 0:
                    time.sleep(1.5)
                else:
                    break
            console.print(f"{self.marker} Received rollout ID: {rollouts[0].rollout_id}")
            
            # skip task if status is not succeeded
            if rollouts[0].status != "succeeded":
                console.print(f"{self.marker} Received rollout ID: {rollouts}")
                console.print(f"{self.marker} Rollout ID: {rollouts[0].rollout_id} is not succeeded")                
                continue
            # optim_span = asyncio.run(store.query_spans(rollout_id=rollouts[0].rollout_id, name="optimizer.output"))
            optim_span = await self.store.query_spans(rollout_id=rollouts[0].rollout_id, name="optimizer.output")
            optim_critique = Critique.model_validate_json(optim_span[0].attributes.get("critique"))
            optim_rewrite = Rewrite.model_validate_json(optim_span[0].attributes.get("rewrite"))
            # updated reward
            updated_reward, updated_target_similarity, updated_retrieved_result = self.evaluator.reward(
                instruction=optim_rewrite.instruction,
                query=task.query,
                target=task.target,
                target_id=task.id
                )
            console.print(f"{self.marker} Updated reward: {updated_reward:.4f}")
            # [`span_id`, `updated-instruction`, `origin-reward`, `delta-reward`]
            steps.append(
                CandidateInstruction(
                    span_id=optim_span[0].span_id,
                    instruction=optim_rewrite.instruction,
                    origin_reward=reward,
                    delta_reward=updated_reward - reward
                )
            )
        return steps

    def get_candidate_instructs(self, beam_n: int=2) -> list[CandidateInstruction]:
        self._history = sorted(self._history, key=lambda x: x.origin_reward + x.delta_reward, reverse=True)
        # pick top 2 best instructions
        candidate_instructs = self._history[:beam_n]
        return candidate_instructs

    def step(self, tasks=list[QueryTask], instructs=list[CandidateInstruction], beam_n: int=2, n_step=0) -> list[CandidateInstruction]:
        updated_instructs = []
        # step each candidate instruction with tasks
        for candi_inst in instructs: 
            submitted_tasks = asyncio.run(self.submit_tasks(tasks=tasks, instruction=candi_inst.instruction))
            pull_queues = list(zip(*submitted_tasks))
            improved_insts = asyncio.run(self.pull_tasks(queues=pull_queues))
            # aggregate reward by tasks for original candidate instruction
            updated_reward = np.mean(list(map(lambda x: x.origin_reward, improved_insts)))
            # update reward for original candidate instruction
            updated_instructs.append(
                CandidateInstruction(
                    span_id=candi_inst.span_id,
                    instruction=candi_inst.instruction,
                    origin_reward=updated_reward,
                    delta_reward=0
                )
            )
            # save improved instruction
            updated_instructs.extend(improved_insts)
        # save updated instructions
        self._history.extend(updated_instructs)
        # sort by reward
        candidate_instructs = self.get_candidate_instructs(beam_n=beam_n)
        console.print(f"{self.marker} Step {n_step}: History {len(self._history)}>> Updated {len(updated_instructs)}>> Candidate {len(candidate_instructs)}")
        return candidate_instructs

    def epoch(self, datasets=list[QueryTask], beam_n: int=2, batch_size=8, epoch=0, train_rate=0.3):
        console.print(f"{self.marker} Epoeh {epoch}")
        random.shuffle(datasets)
        epoch_steps = len(datasets) // batch_size
        train_session_step = int(epoch_steps * train_rate)
        candidate_instructs = self.get_candidate_instructs(beam_n=beam_n)
        for n_step in range(max(train_session_step, 1)):
            candidate_instructs = self.step(
                tasks=datasets[n_step*batch_size: (n_step+1)*batch_size],
                instructs=candidate_instructs,
                beam_n=beam_n,
                n_step=n_step
                )
        return candidate_instructs

    def evolute(self) -> CandidateInstruction:
        evolution_df = pa.Table.from_pylist(list(map(lambda x: x.model_dump(), self._history)))
        decl = Declaration.from_sequence([
            Declaration("table_source", TableSourceNodeOptions(evolution_df)),
            Declaration("project", ProjectNodeOptions(
                list(map(pc.field, evolution_df.column_names)) + [pc.add(pc.field("origin_reward"), pc.field("delta_reward"))],
                evolution_df.column_names + ["step_reward"]
            )),
            Declaration("aggregate", AggregateNodeOptions(
                [
                    ("instruction", "hash_one", None, "instruction"),
                    ("origin_reward", "hash_mean", None, "origin_reward"),
                    ("delta_reward", "hash_mean", None, "delta_reward"),
                    ("step_reward", "hash_mean", None, "step_reward"),
                    ("span_id", "hash_count", None, "count")
                ],
                keys=["span_id"]
            )),
            Declaration("filter", FilterNodeOptions(pc.greater(pc.field("delta_reward"), 0.0) & pc.greater(pc.field("count"), 1))),
            Declaration("order_by", OrderByNodeOptions([("step_reward", "descending")])),
        ])
        result = decl.to_table()
        del decl
        if len(result) == 0:
            decl = Declaration.from_sequence([
                Declaration("table_source", TableSourceNodeOptions(evolution_df)),
                Declaration("project", ProjectNodeOptions(
                    list(map(pc.field, evolution_df.column_names)) + [pc.add(pc.field("origin_reward"), pc.field("delta_reward"))],
                    evolution_df.column_names + ["step_reward"]
                )),
                Declaration("aggregate", AggregateNodeOptions(
                    [
                        ("instruction", "hash_one", None, "instruction"),
                        ("origin_reward", "hash_mean", None, "origin_reward"),
                        ("delta_reward", "hash_mean", None, "delta_reward"),
                        ("step_reward", "hash_mean", None, "step_reward"),
                        ("span_id", "hash_count", None, "count")
                    ],
                    keys=["span_id"]
                )),
                Declaration("filter", FilterNodeOptions(pc.greater(pc.field("count"), 1))),
                Declaration("order_by", OrderByNodeOptions([("step_reward", "descending")])),
            ])
            result = decl.to_table()
            del decl
        del evolution_df
        return CandidateInstruction(**result.take([0]).to_pylist()[0])

