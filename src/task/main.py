import os
from agentlightning.types import PromptTemplate
from agentlightning.store import LightningStoreClient
from rich.console import Console
from src.task.utils import Encoder, VectorStore
from src.task.evaluator import Evaluator


console = Console()
marker = "[bold #afff00][Main][/bold #afff00]"

def tuner_setups():
    encoder = Encoder(
        name=os.getenv("EMBED_MODEL"),
        base_url=os.getenv("EMBED_BASE_URL"),
        api_key=os.getenv("API_KEY"),
        dim=int(os.getenv("EMBED_DIM"))
    )

    # init vector_store
    console.print(f"{marker} Connect to LanceDB")
    if os.getenv("LANCEDB_ENDPOINT"):
        storage_options = {
            "region_name": os.getenv("LANCEDB_REGION"),
            "endpoint": os.getenv("LANCEDB_ENDPOINT"),
            "aws_access_key_id": os.getenv("LANCEDB_AWS_ACCESS_KEY_ID"),
            "aws_secret_access_key": os.getenv("LANCEDB_AWS_SECRET_ACCESS_KEY"),
            "allow_http": os.getenv("LANCEDB_ALLOW_HTTP")
        }
    else:
        storage_options = None
    vector_store = VectorStore(
        encoder=encoder,
        table_name=os.getenv("TABLE_NAME"),
        uri=os.getenv("LANCEDB_URI"),
        storage_options=storage_options,
        vector_column=os.getenv("LANCEDB_VECTOR_COLUMN"),
        query_column=os.getenv("LANCEDB_QUERY_COLUMN"),
        target_column=os.getenv("LANCEDB_TARGET_COLUMN"),
    )
    datasets = vector_store.to_ragset()
    console.print(f"{marker} Number of datasets: {len(datasets)}")

    ## init evaluator
    evaluator = Evaluator(
        prompt_template=PromptTemplate(
        template="Instruct: {instruction}\nQuery: {query}",
        engine="f-string"
        ),
        vector_store=vector_store
    )

    ## Connect to Lightning store
    console.print(f"{marker} Connect to lightning store")
    store = LightningStoreClient(os.getenv("LIGHTNING_STORE_URL"))
    return encoder, vector_store,  datasets, evaluator, store

if __name__ == "__main__":
    from src.task.tuner import Tuner
    import pyarrow as pa
    import pyarrow.parquet as pq
    import asyncio
    import uuid
    import json
    from dotenv import load_dotenv
    load_dotenv()
    

    # setup tuning instance
    encoder, vector_store,  datasets, evaluator, store = tuner_setups()
    # tuning arguments
    batch_size = 8; epochs = 3; beam_n = 2; train_rate = 0.6

    # initial tuner
    tuner_id = str(uuid.uuid4())
    tuner = Tuner(store=store, evaluator=evaluator, history=None)
    # initial templates to resources
    resources = asyncio.run(store.add_resources({
        "prompt_template": evaluator.prompt_template,
        "instruction": PromptTemplate(
            template=json.dumps({
                "instruction": tuner._history[0].instruction,
                "reward":tuner._history[0].origin_reward + tuner._history[0].delta_reward,
            }),
            engine="f-string"
        ),
        "info": PromptTemplate(
            template=json.dumps({
                "epoch": -1,
                "tuner_id": tuner_id
            }),
            engine="f-string"
            )}))

    # main training
    final_reward = []
    for epoch in range(epochs):
        # run an epoch
        candidate_instructions = tuner.epoch(datasets=datasets, beam_n=beam_n, batch_size=batch_size, epoch=epoch, train_rate=train_rate)
        # pick instruction
        instruction = tuner.evolve()
        epoch_reward = instruction.origin_reward + instruction.delta_reward
        # update templates to resources
        updated_resources = asyncio.run(store.add_resources({
            "prompt_template": evaluator.prompt_template,
            "instruction": PromptTemplate(
                template=json.dumps({
                    "instruction": instruction.instruction,
                    "reward": epoch_reward
                }),
                engine="f-string"
            ),
            "info": PromptTemplate(
                template=json.dumps({
                    "epoch": epoch,
                    "tuner_id": tuner_id
                }),
                engine="f-string"
            )
            }))
        final_reward.append([epoch, updated_resources.resources_id, epoch_reward])
    for reward in final_reward:
        console.print(f"{marker} Reward: {reward}")

    history_df = pa.Table.from_pylist(list(map(lambda x: x.model_dump(), tuner._history)))
    try:
        os.mkdir("./storage")
    except:
        pass
    pq.write_table(history_df, f"./storage/history-{tuner_id}.parquet")
    console.print(f"{marker} Save history to storage. Path: ./storage/history-{tuner_id}.parquet")
