from agentlightning.types import PromptTemplate
from pydantic import BaseModel

class BaseTemplate:
    """Base class for task templates providing schema and prompt access."""
    
    @property
    def schema(self) -> str:
        """Returns the JSON schema for the task output."""
        raise NotImplementedError
        
    @property
    def prompt(self) -> PromptTemplate:
        """Returns the PromptTemplate object for the task."""
        raise NotImplementedError

# Critique

class Critique(BaseModel):
    textual_gradient: str

class CritiqueTemplate(BaseTemplate):
    _SCHEMA = (
        "{{\n"
        "  'textual_gradient': <1-2 strong imperative sentences telling the Rewrite LLM how to improve the instruction>\n"
        "}}\n"
        )

    @property
    def schema(self) -> str:
        return self._SCHEMA

    @property
    def prompt(self) -> PromptTemplate:
        template_str = (
            "You are a Critique LLM.\n"
            "Your ONLY job is to generate a concise, actionable `textual gradient` that tells a Rewrite LLM how to improve the given <instruction> for better RAG retrieval.\n\n"
            "INPUT:\n"
            "- <instruction> {instruction} </instruction>\n"
            "- <query> {query} </query>\n"
            "- <target_content> {target_content} </target_content>\n"
            "- <target_similarity> {target_similarity} </target_similarity>\n"
            "- <retrieved_contents> {retrieved_contents} </retrieved_contents>\n"
            "- <retrieved_similarities> {retrieved_similarities} </retrieved_similarities>\n\n"
            "OBJECTIVE:\n"
            "1. Make (<instruction> + <query>) MORE semantically similar to <target_content>\n"
            "2. Make (<instruction> + <query>) LESS semantically similar to non-target <retrieved_contents>\n\n"
            "CONSTRAINTS:\n"
            "- Do NOT change the user's intent.\n"
            "- Do NOT invent facts.\n"
            "- Only critique and suggest changes to the <instruction> text itself.\n"
            "- Base your suggestions on the similarity values.\n"
            "- Be concrete and directive.\n\n"
            "OUTPUT (strict JSON):\n"
            "```json\n"
        ) + self._SCHEMA + (
            "\n```\n"
            "RULES:\n"
            "- If any retrieved similarity (non-target) is >= target_similarity, you MUST introduce stricter constraints and/or negative filters.\n"
            "- **The `textual gradient` MUST be a single, short sentence in English.**\n"
            "- Be short. Be sharp. Be operational.\n"
            "- Everything you output should be usable directly by a Rewrite LLM.\n"
        )
        return PromptTemplate(template=template_str, engine="f-string")


class Rewrite(BaseModel):
    instruction: str

class RewriteTemplate(BaseTemplate):
    _SCHEMA = (
        "{{\n"
        "  'instruction': <improved instruction>,\n"
        "}}\n"
        )

    @property
    def schema(self) -> str:
        return self._SCHEMA

    @property
    def prompt(self) -> PromptTemplate:
        template_str = (
            "You are a Rewrite LLM. Generate an improved <instruction> that:\n"
            "1. Preserves the original user's intent\n"
            "2. Implements the critique's `textual_gradient`\n\n"
            "You receive:\n"
            "- <instruction> {instruction} </instruction>\n"
            "- <critique> {critique} </critique>\n\n"
            "CONSTRAINTS:\n"
            "- The rewritten instruction **MUST BE IN ENGLISH**.\n"
            "- Do NOT change the original user's intent.\n"
            "- Do NOT invent facts.\n"
            "- Keep the rewritten instruction **extremely concise (must be a single, short sentence)**.\n\n"
            "OUTPUT (strict JSON, containing only the improved instruction in the `instruction` field):\n"
            "```json\n"
        ) + self._SCHEMA + ("\n```\n")
        return PromptTemplate(template=template_str, engine="f-string")
