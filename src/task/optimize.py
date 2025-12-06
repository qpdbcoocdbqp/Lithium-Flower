from openai import AsyncOpenAI
from typing import Any
from src.task.model import (
    Critique,
    Rewrite,
    CritiqueTemplate,
    RewriteTemplate
)


class APOptimizerBase:
    def __init__(self, async_openai_client: AsyncOpenAI):
        self.async_openai_client = async_openai_client

    async def _chat(self, model :str, messages: list, diversity_temperature: float,
        max_completion_tokens: int=512, reasoning_effort: str="none"):
        response = await self.async_openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=diversity_temperature,
            max_completion_tokens=max_completion_tokens,
            reasoning_effort=reasoning_effort
        )
        return response.choices[0].message.content

    async def _parse(self, model :str, messages: list, response_format: Any,
                     diversity_temperature=0.0, max_completion_tokens: int=512, reasoning_effort: str="none"):
        response = await self.async_openai_client.chat.completions.parse(
            model=model,
            messages=messages,
            temperature=diversity_temperature,
            response_format=response_format,
            max_completion_tokens=max_completion_tokens,
            reasoning_effort=reasoning_effort
        )
        return response.choices[0].message.parsed

    def _output_schema_parse_messages(self, content: str, output_schema: str) -> list[dict]:
        parse_messages = [
            {"role": "system", "content": (
                "Your task to extract user content into <output_schema>:\n\n"
                "OUTPUT (strict JSON):\n<output_schema>\n\n"
                "```json\n{output_schema}\n```\n</output_schema>\n\n"
                ).format(output_schema=output_schema)},
            {"role": "user", "content": content}
            ]
        return parse_messages

class RAGOptimizer(APOptimizerBase):
    def __init__(self, async_openai_client: AsyncOpenAI, critique_model: str, rewrite_model: str=None, parse_model: str=None, diversity_temperature: float=0.2):
        super().__init__(async_openai_client)
        self.critique_model = critique_model
        self.rewrite_model = rewrite_model if rewrite_model else critique_model
        self.parse_model = parse_model if parse_model else critique_model
        self.diversity_temperature = diversity_temperature
        self.critique_template = CritiqueTemplate()
        self.rewrite_template = RewriteTemplate()
        pass
    
    async def critique(self, inputs: dict) -> Critique:
        critique_response = await self._parse(
            model=self.critique_model,
            messages=[
                {"role": "system", "content": self.critique_template.prompt.template.format(**inputs)},
                {"role": "user", "content": "What is the critiques for rewritting?"}
                ],
            diversity_temperature=self.diversity_temperature,
            response_format=Critique
            )
        return critique_response
    
    async def rewrite(self, critiques: dict) -> Rewrite:
        rewrite_response = await self._parse(
            model=self.rewrite_model,
            messages=[
                {"role": "system", "content": self.rewrite_template.prompt.template.format(**critiques)},
                {"role": "user", "content": "Start the rewrite task."}
                ],
            diversity_temperature=self.diversity_temperature,
            response_format=Rewrite)
        return rewrite_response
    
    async def critique_two_step(self, inputs: dict) -> Critique:
        messages = [
            {"role": "system", "content": self.critique_template.prompt.template.format(**inputs)},
            {"role": "user", "content": "What is the critiques for rewritting?"}
            ]
        middle_content = await self._chat(model=self.critique_model, messages=messages, diversity_temperature=self.diversity_temperature)
        parse_messages = self._output_schema_parse_messages(content=middle_content, output_schema=self.critique_template.schema)
        critique_response = await self._parse(model=self.parse_model, messages=parse_messages, response_format=Critique)
        return critique_response

    async def rewrite_two_step(self, critiques: dict) -> Rewrite:
        messages = [
            {"role": "system", "content": self.rewrite_template.prompt.template.format(**critiques)},
            {"role": "user", "content": "Start the rewrite task."}
            ]
        middle_content = await self._chat(model=self.rewrite_model, messages=messages, diversity_temperature=self.diversity_temperature)
        parse_messages = self._output_schema_parse_messages(content=middle_content, output_schema=self.rewrite_template.prompt.schema)
        rewrite_response = await self._parse(model=self.parse_model, messages=parse_messages, response_format=Rewrite)
        return rewrite_response
