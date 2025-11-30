import asyncio
import agentlightning as agl

store = agl.store.LightningStoreClient("http://localhost:45993")

rollouts = asyncio.run(store.query_rollouts())
print(rollouts)
