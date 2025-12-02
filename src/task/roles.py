from openai import AsyncOpenAI
from src.task import prompt


class APOBase:
    def __init__(self, async_openai_client: AsyncOpenAI):
        self.async_openai_client = async_openai_client

    async def _chat(self, model :str, messages: list, diversity_temperature: float):
        response = await self.async_openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=diversity_temperature,
        )
        return response.choices[0].message.content

class RAG(APOBase):
    def __init__(self, async_openai_client: AsyncOpenAI, critique_model: str, rewrite_model: str=None, diversity_temperature: float=0.2):
        super().__init__(async_openai_client)
        self.critique_model = critique_model
        if rewrite_model is None:
            self.rewrite_model = critique_model
        else:
            self.rewrite_model = rewrite_model
        self.diversity_temperature = diversity_temperature
        pass
    
    async def critique(self, inputs: dict):
        messages = [{"role": "system", "content": prompt.critique_prompt.format(**inputs)}]
        critique_response = await self._chat(self.critique_model, messages, self.diversity_temperature)        
        return critique_response

    async def rewrite(self, critiques: dict):
        messages = [{"role": "system", "content": prompt.rewrite_prompt.format(**critiques)}]
        rewrite_response = await self._chat(self.rewrite_model, messages, self.diversity_temperature)
        return rewrite_response
