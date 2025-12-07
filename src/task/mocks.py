import os
from agentlightning.types import PromptTemplate
from agentlightning.store import LightningStoreClient
from agentlightning import Span, find_final_reward
from rich.console import Console
from src.task.utils import Encoder, VectorStore
from src.task.evaluator import Evaluator


console = Console()

def tuner_setups():
    from dotenv import load_dotenv
    load_dotenv()
    # init vector_store
    console.print(f"[bold yellow][LanceDB][/bold yellow] Connect to LanceDB")
    encoder = Encoder(
        name=os.getenv("EMBED_MODEL"),
        base_url=os.getenv("EMBED_BASE_URL"),
        api_key=os.getenv("API_KEY"),
        dim=int(os.getenv("EMBED_DIM"))
        )
    vector_store = VectorStore(encoder=encoder, table_name=os.getenv("TABLE_NAME"), uri=os.getenv("LANCEDB_URI"))
    datasets = vector_store.to_ragset()
    console.print(f"[bold yellow][LanceDB][/bold yellow] Number of datasets: {len(datasets)}")
    ## init evaluator
    evaluator = Evaluator(
        prompt_template=PromptTemplate(
            template="Instruct: {instruction}\nQuery: {query}",
            engine="f-string"
            ),
        vector_store=vector_store
        )
    ## Connect to Lightning store
    console.print(f"[bold yellow][LIGHTNING_STORE][/bold yellow] Connect to lightning store")
    store = LightningStoreClient(os.getenv("LIGHTNING_STORE_URL"))
    return encoder, vector_store,  datasets, evaluator, store

# --- main
from src.task.tuner import Tuner
# from src.task.utils import QueryTask
import asyncio
import uuid
# import random
import json

atch_size = 8; epoch = 0; beam_n = 2; train_rate = 0.1
encoder, vector_store,  datasets, evaluator, store = tuner_setups()

tuner_id = str(uuid.uuid4())

tuner = Tuner(store=store, evaluator=evaluator, history=None)
resources = asyncio.run(store.add_resources({
    "prompt_template": evaluator.prompt_template,
    "instruction": PromptTemplate(
        template=json.dumps({
            "instruction": tuner._history[0].instruction,
            "reward": 0.0,
        }),
        engine="f-string"
    )
}))

candidate_instructions = tuner.epoch(datasets=datasets, beam_n=2, batch_size=4, epoch=0, train_rate=0.1)
instruction = tuner.evolve()

epoch_id = f"ro-{tuner_id}-epoch-{epoch}"

reward_span = Span.from_attributes(
    rollout_id=epoch_id,
    attempt_id=epoch_id,
    name="agentlightning.reward",
    attributes={
        "reward": instruction.origin_reward + instruction.delta_reward,
        **instruction.model_dump()
    }
    )

asyncio.run(store.add_otel_span(reward_span))
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
# TypeError: LightningStoreClient.add_otel_span() missing 2 required positional arguments: 'attempt_id' and 'readable_span'

final_reward = find_final_reward([reward_span])


