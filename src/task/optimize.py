from openai import AsyncOpenAI
from typing import Any, Optional, List
import agentlightning as agl
from src.task.model import (
    Critique,
    Rewrite,
    CritiqueTemplate,
    RewriteTemplate
)
from rich.console import Console
console = Console()

class APOptimizerBase:
    # Maximum size for span attributes (in characters)
    MAX_ATTRIBUTE_SIZE = 1024
    
    def __init__(self, async_openai_client: AsyncOpenAI, rollout_id: Optional[str] = None, attempt_id: Optional[str] = None):
        self.async_openai_client = async_openai_client
        self.rollout_id = rollout_id
        self.attempt_id = attempt_id
        self.spans: List[agl.Span] = []  # Collect spans to return
    
    def _truncate_attribute(self, value: str, max_size: int = None) -> str:
        """Truncate attribute value if it exceeds max size."""
        if not value:
            return ""
        max_size = max_size or self.MAX_ATTRIBUTE_SIZE
        if len(value) > max_size:
            return value[:max_size] + "... [TRUNCATED]"
        return value

    async def _chat(self, model :str, messages: list, diversity_temperature: float,
                    max_completion_tokens: int=512, reasoning_effort: str="none",
                    sequence_id=0):
        # Call OpenAI API
        response = await self.async_openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=diversity_temperature,
            max_completion_tokens=max_completion_tokens,
            reasoning_effort=reasoning_effort
        )
        content = response.choices[0].message.content
        
        # Create AgentLightning Span if rollout_id and attempt_id are provided
        if self.rollout_id and self.attempt_id:
            # console.print(f"[bold green][CREATE SPAN][/bold green] openai.chat.completions.create for {self.rollout_id}")
            span = agl.Span.from_attributes(
                rollout_id=self.rollout_id,
                attempt_id=self.attempt_id,
                sequence_id=sequence_id,
                name="openai.chat.completions.create",
                attributes={
                    "model": model,
                    "temperature": diversity_temperature,
                    "max_completion_tokens": max_completion_tokens,
                    "response.finish_reason": response.choices[0].finish_reason,
                    "response.content": self._truncate_attribute(content if content else ""),
                }
            )
            self.spans.append(span)
        
        return content

    async def _parse(self, model :str, messages: list, response_format: Any,
                     diversity_temperature=0.0, max_completion_tokens: int=512, reasoning_effort: str="none",
                     sequence_id=0):
        # Call OpenAI API
        response = await self.async_openai_client.chat.completions.parse(
            model=model,
            messages=messages,
            temperature=diversity_temperature,
            response_format=response_format,
            max_completion_tokens=max_completion_tokens,
            reasoning_effort=reasoning_effort
        )
        parsed = response.choices[0].message.parsed
        
        # Create AgentLightning Span if rollout_id and attempt_id are provided
        if self.rollout_id and self.attempt_id:
            # console.print(f"[bold green][CREATE SPAN][/bold green] openai.chat.completions.parse for {self.rollout_id}")
            # Convert parsed object to JSON string
            parsed_str = ""
            if parsed:
                import json
                try:
                    parsed_str = parsed.model_dump_json() if hasattr(parsed, 'model_dump_json') else json.dumps(str(parsed))
                except Exception:
                    parsed_str = str(parsed)
            
            span = agl.Span.from_attributes(
                rollout_id=self.rollout_id,
                attempt_id=self.attempt_id,
                sequence_id=sequence_id,
                name="openai.chat.completions.parse",
                attributes={
                    "model": model,
                    "temperature": diversity_temperature,
                    "max_completion_tokens": max_completion_tokens,
                    "response_format": response_format.__name__ if hasattr(response_format, '__name__') else str(response_format),
                    "response.finish_reason": response.choices[0].finish_reason,
                    "response.parsed": self._truncate_attribute(parsed_str),
                }
            )
            self.spans.append(span)
        
        return parsed

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
    def __init__(self, async_openai_client: AsyncOpenAI, critique_model: str, rewrite_model: str=None, parse_model: str=None, diversity_temperature: float=0.2, rollout_id: Optional[str] = None, attempt_id: Optional[str] = None):
        super().__init__(async_openai_client, rollout_id, attempt_id)
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
            response_format=Critique,
            sequence_id=1
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
            response_format=Rewrite,
            sequence_id=2)
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
