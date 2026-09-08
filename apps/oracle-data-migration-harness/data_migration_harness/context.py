"""Layer 6: explicit context builder. Builds prompts from named slots."""

from dataclasses import dataclass
from pathlib import Path

INSTR = Path(__file__).parent / "instructions"


@dataclass
class ChatContext:
    side: str
    user_question: str
    tool_descriptions: str
    retrieved_examples: str = ""

    def to_prompt(self) -> str:
        return f"""You are the chat agent on the {self.side} side of a database migration demo.

Available tools:
{self.tool_descriptions}

{self.retrieved_examples}

User question: {self.user_question}

Decide which tool to call. If the question is open-ended and semantic, prefer vector search.
If the question asks for aggregation, counting, or filtering by structured fields, prefer the SQL tool.
"""


def load_system_prompt() -> str:
    return (INSTR / "system_prompt.md").read_text()


def load_skill(name: str) -> str:
    return (INSTR / f"{name}.md").read_text()
