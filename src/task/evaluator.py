import numpy as np
from pydantic import BaseModel
from rich.console import Console
from agentlightning.types import PromptTemplate
from task.utils import VectorStore


console = Console()

class BiasWeight(BaseModel):
    target_weight: float = 0.25
    target_content_weight: float = 0.25
    distance_weight: float = 0.5

def reward_function(
    target_similarity,
    target_content_similarity,
    retrieved_distance,
    bias_weight: BiasWeight
    ):
    return (
        bias_weight.target_weight * target_similarity +
        bias_weight.target_content_weight * target_content_similarity +
        bias_weight.distance_weight * np.mean(target_content_similarity - retrieved_distance)
    )

class Evaluator():
    def __init__(self, prompt_template: PromptTemplate, vector_store: VectorStore, bias_weight: dict=None):
        self.eval_marker = "[bold dark_orange][Evaluator][/bold dark_orange]"
        self.prompt_template = prompt_template
        self.vector_store = vector_store
        self.bias_weight = BiasWeight(**bias_weight) if bias_weight else BiasWeight()
        pass

    def _target_similarity(self, prompt: str, target: str):
        query_emb, target_emb = self.vector_store.encoder.generate_embeddings([prompt, target])
        similarity = np.dot(query_emb, target_emb)
        del target_emb
        return similarity, query_emb

    def _target_content_similarity(self, embedding, target_id):
        content = (self.vector_store._table.search()
            .where(f"id_ == '{target_id}'")
            .limit(1)
            .select(["id_", "embedding"])
            .to_list()[0])
        similarity = np.dot(embedding, content.get("embedding"))
        del content
        return similarity

    def _retrieved_distance(self, query, target_id):
        contents = self.vector_store.search(query=query)
        distances = [row.get("_distance") for row in contents if row.get("id_") != target_id]
        return distances, contents

    def reward(self, instruction: str, query: str, target: str, target_id):
        embedding_prompt = self.prompt_template.format(instruction=instruction, query=query)
        # target similarity
        target_similarity, query_emb = self._target_similarity(prompt=embedding_prompt, target=target)
        console.print(f"{self.eval_marker} Target similarity: {target_similarity:.4f}")
        # target content similarity
        target_content_similarity = self._target_content_similarity(embedding=query_emb, target_id=target_id)        
        console.print(f"{self.eval_marker} Target content similarity: {target_content_similarity:.4f}")
        # retrieved distance
        retrieved_distance, retrieved_result = self._retrieved_distance(query=query_emb, target_id=target_id)
        console.print((f"{self.eval_marker} Retrieved distance: {{dists}}").format(
            dists=["{dist:.4f}".format(dist=dist) for dist in retrieved_distance]
            ))
        reward = reward_function(
            target_similarity=target_similarity,
            target_content_similarity=target_content_similarity,
            retrieved_distance=retrieved_distance,
            bias_weight=self.bias_weight
            )
        console.print(f"{self.eval_marker} Reward: {reward:.4f}")
        del embedding_prompt, query_emb, target_content_similarity, retrieved_distance
        return reward, target_similarity, retrieved_result
