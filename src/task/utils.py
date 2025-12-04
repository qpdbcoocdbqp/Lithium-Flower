import random
import lancedb
import numpy as np
from lancedb.embeddings import EmbeddingFunctionConfig, EmbeddingFunction, OpenAIEmbeddings
from typing import Optional, Sequence, Tuple, Union
from rich.console import Console
from agentlightning.types import Dataset
from dataclasses import dataclass
from typing import cast


console = Console()

class Encoder(OpenAIEmbeddings):
    def ndims(self):
        return self.dim

class EncoderWrapper(EmbeddingFunction):
    def __init__(self, encoder: OpenAIEmbeddings) -> None:
        super().__init__()
        self._encoder = encoder
        self._ndims = encoder.dim
        pass
    
    def compute_query_embeddings(self, query, *args, **kwargs) -> list[Union[np.array, None]]:
        if isinstance(query, str):
            return self._encoder.generate_embeddings(texts=[query])
        return self._encoder.generate_embeddings(texts=query)
    
    def compute_source_embeddings(self, texts, *args, **kwargs) -> list[Union[np.array, None]]:
        if isinstance(texts, str):
            return self._encoder.generate_embeddings(texts=[texts])
        return self._encoder.generate_embeddings(texts=texts)
    
    def ndims(self) -> int:
        return self._ndims

# RAG dataset
@dataclass
class QueryTask:
    id: str
    query: str
    target: str

def to_ragset(data: list[dict]) -> Dataset[QueryTask]:
    dataset = cast(Dataset[QueryTask], [
        QueryTask(id=row.get("id_"), query=row.get("metadata.query"), target=row.get("metadata.target"))
        for row in data
        ])
    return dataset

# --- Vector Store ---
class VectorStore():
    def __init__(self, encoder: OpenAIEmbeddings, table_name: str, uri: str = None, storage_options: dict = None):
        # Database of (text, vector)
        self.encoder = encoder
        self.embedding_config = EmbeddingFunctionConfig(
            vector_column="vector",
            source_column="text",
            function=EncoderWrapper(self.encoder)
            )
        self._conn = lancedb.connect(
            uri=uri,
            storage_options=storage_options
        )
        console.print(f"[bold yellow][VectorStore][/bold yellow] Connect success")
        self._table = self._conn.open_table(table_name)
        console.print(f"[bold yellow][VectorStore][/bold yellow] Open table success")
        self._table.embedding_functions.update({"embedding": self.embedding_config})
        console.print(f"[bold yellow][VectorStore][/bold yellow] Update embedding fuction success")
        self.population = None
        pass
    
    def search(self, query: Union[str, np.array]) -> list[dict]:
        if isinstance(query, str):
            query_vec = self.encoder.generate_embeddings([query])[0]
        else:
            query_vec = query
        result = self._table.search(
            query=query_vec, query_type="vector"
            ).metric("cosine").limit(5).select(["id_", "text", "_distance"]).to_list()
        del query_vec
        return result
    
    def _population(self):
        if self.population is None:
            self.population = self._table.search().select(
                ["id_", "metadata.query", "metadata.target"]
                ).to_list()
        pass

    def sample(self, n: int):
        self._population()
        random.shuffle(self.population)
        return self.population[:min(n, len(self.population))]

    def to_ragset(self) -> Dataset[QueryTask]:
        self._population()
        return to_ragset(self.population)
