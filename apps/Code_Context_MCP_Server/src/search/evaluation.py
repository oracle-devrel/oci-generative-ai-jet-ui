"""Retrieval evaluation: recall of a gold set of questions and the paths expected among their top results
(specs/011-usage-feedback, US4, research R10).
"""

import json
from dataclasses import dataclass
from pathlib import Path

from golestan_code_mcp import registry
from golestan_code_mcp.search import query


def load_gold(path, conn) -> list[dict]:
    """The questions of a gold file, checked: each has words, expected paths, and a registered repository if any."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ValueError(f"gold file not found: {path}") from None
    try:
        gold = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"gold file is not valid JSON: {e}") from None
    if not isinstance(gold, dict) or not isinstance(gold.get("version"), int):
        raise ValueError("gold file: no version")
    questions = gold.get("questions")
    if not isinstance(questions, list) or not questions:
        raise ValueError("gold file: no questions")
    for n, q in enumerate(questions, 1):
        if not isinstance(q, dict) or not str(q.get("question") or "").strip():
            raise ValueError(f"gold file: question {n} is empty")
        if not isinstance(q.get("paths"), list) or not q["paths"]:
            raise ValueError(f"gold file: question {n} has no paths")
        if q.get("repo"):
            try:
                registry.repo_id(conn, q["repo"])
            except ValueError as e:
                raise ValueError(f"{e} (gold question {n})") from None
    return questions


def matches(path: str, expected: list[str]) -> bool:
    """A hit's path is expected: the same file, or a file under an expected directory."""
    return any(path == e or path.startswith(e.rstrip("/") + "/") for e in expected)


@dataclass(frozen=True)
class Evaluation:
    questions: int
    hits: int
    missed: list[str]

    @property
    def recall(self) -> float:
        return self.hits / self.questions


def evaluate(conn, gold: list[dict], with_feedback: bool, limit: int = 10) -> Evaluation:
    """recall@limit: a question is a hit when any of its top `limit` results is at an expected path. Records nothing."""
    missed = [q["question"] for q in gold
              if not any(matches(h.path, q["paths"]) for h in query.search(
                  conn, q["question"], [q["repo"]] if q.get("repo") else None, limit=limit, feedback=with_feedback))]
    return Evaluation(len(gold), len(gold) - len(missed), missed)
