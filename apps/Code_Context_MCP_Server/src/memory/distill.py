"""Agent memory distillation: a finding's text, from the local template or from a configured model.

A model's text is kept only when every code name it uses is in its input (unknown_names).
"""

import json
import logging
import re
from dataclasses import dataclass

from golestan_code_mcp import __version__
from golestan_code_mcp.memory import findings as memory_findings

log = logging.getLogger("golestan_code_mcp.memory")

CONSOLIDATOR = f"memory/{__version__}"
TEMPLATE = "template/1"


@dataclass
class _Fact:
    id: str | None
    meta: dict
    text: str = ""
    changed: bool = False
    weakened: bool = False


def _contradict(fact: _Fact) -> None:
    fact.meta["contradict"] += 1
    fact.changed = fact.weakened = True


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _quoted(names: list[str]) -> str:
    return ", ".join(f"`{n}`" for n in names)


def template_text(meta: dict) -> str:
    """The template distiller: what the findings say, in sentences, and nothing more."""
    s, kind, path, f = meta["subject"], meta["kind"], meta["path"], meta["findings"]
    if kind == "page":
        summary = f.get("module", {}).get("summary", "").strip()
        parts = [f"`{s}` is the wiki page for `{path}`." + (f" {summary.rstrip('.')}." if summary else "")]
    else:
        parts = [f"`{s}` is a {kind} in `{path}`."]
        if (n := f.get("defined", {}).get("definitions") or 0) > 1:
            parts.append(f"It is one of {n} definitions named `{s.rsplit('.', 1)[-1]}`.")
    if (c := f.get("callers")) and c["count"]:
        parts.append(f"It is called by {_plural(c['count'], 'symbol')}, including {_quoted(c['names'])}.")
    if (c := f.get("callees")) and c["count"]:
        parts.append(f"It calls {_plural(c['count'], 'indexed symbol')}, including {_quoted(c['names'])}.")
    if (c := f.get("impact")) and c["count"]:
        parts.append(f"A change to it reaches {_plural(c['count'], 'symbol')} within {c['depth']} call hops, nearest"
                     f" first: {_quoted(c['names'])}.")
    if meta["questions"]:
        parts.append("Asked as " + ", ".join(f'"{q}"' for q in meta["questions"][:3]) + ".")
    return " ".join(parts)


WORD = re.compile(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*")
CODE = re.compile(r"\w*_\w+|[a-z]+[A-Z]\w*|[A-Z][a-z0-9]+[A-Z]\w*|[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+")
SPAN = re.compile(r"`([^`\n]+)`")


def _names_in(text: str) -> list[str]:
    """The code identifiers a text names: a backticked identifier, and code-shaped words (snake_case, CamelCase,
    dotted) anywhere. Inside a backticked phrase only code-shaped words count, so prose caught between unpaired
    backticks is not taken for a name."""
    found = []
    for span in SPAN.findall(text):
        whole = span.strip().removesuffix("()")
        found += [whole] if WORD.fullmatch(whole) else [w for w in WORD.findall(span) if CODE.fullmatch(w)]
    found += [w for w in WORD.findall(SPAN.sub(" ", text)) if CODE.fullmatch(w)]
    return list(dict.fromkeys(found))


def unknown_names(text: str, allowed: set[str]) -> list[str]:
    """The identifiers the text names that appear nowhere in what was allowed (research R13).

    A dotted name passes when each of its parts appears, so `pkg.widgets` matches the path pkg/widgets.py.
    """
    known = {w for a in allowed for w in WORD.findall(a)}
    parts = known | {p for k in known for p in k.split(".")}
    return [n for n in _names_in(text) if n not in known and not all(p in parts for p in n.split("."))]


def _source(cur, repo_id: int, meta: dict) -> str:
    if meta["kind"] == "page":
        page = memory_findings._page(cur, repo_id, meta["subject"])
        text = page["text"] if page else ""
    else:
        row = cur.execute("""select s.source from ccctx_symbols s join ccctx_files f on f.id = s.file_id
                              where f.repo_id = :r and s.name = :n and s.kind = :k and f.path = :p
                              fetch first 1 rows only""", r=repo_id, n=meta["subject"], k=meta["kind"],
                          p=meta["path"]).fetchone()
        text = (row[0].read() if hasattr(row[0], "read") else row[0]) if row else ""
    return "\n".join(text.split("\n")[:memory_findings.SOURCE_LINES])


ANSWER = {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}


def _prompt(cur, repo_id: int, meta: dict) -> str:
    """Exactly what research R13 says is sent: the subject's source, its findings, related code, the questions."""
    findings = {a: {k: v for k, v in f.items() if k not in ("tool", "arguments", "run")}
                for a, f in meta["findings"].items()}
    related = [f"- `{r['name']}` ({r['kind']}) in `{r['path']}`" for r in meta["refs"] if r["role"] == "related"]
    return "\n".join([
        "Write at most 3 sentences stating what the findings and the source below show about the subject. Name only"
        " code that appears below, in backticks. Reply as JSON: {\"text\": \"...\"}.",
        "", f"Subject: `{meta['subject']}` ({meta['kind']}) in `{meta['path']}`",
        "", "Source:", _source(cur, repo_id, meta),
        "", "Findings:", json.dumps(findings, sort_keys=True),
        "", "Related code:", *(related or ["- none"]),
        "", "Questions asked:", *(f"- {q}" for q in meta["questions"]),
    ])


def _distill(cur, repo_id: int, repo: str, meta: dict, llm) -> tuple[str, str]:
    """(text, distiller): the configured model's text when it is valid, else the template's."""
    template = template_text(meta)
    if llm is None:
        return template, TEMPLATE
    model_, name = llm
    prompt = _prompt(cur, repo_id, meta)
    try:
        text = json.loads(model_.generate(prompt, response_json_schema=ANSWER).text)["text"]
        text = text.strip()
        if not text:
            raise ValueError("empty text")
    except Exception as e:  # noqa: BLE001 - any model failure falls back; consolidation goes on
        log.warning(json.dumps({"event": "memory_model_failed", "repo": repo, "reason": type(e).__name__}))
        return template, TEMPLATE
    sent = prompt.split("\n\nSubject:", 1)[1]  # everything it was given about the code, not the instructions
    if bad := unknown_names(text, {sent}):
        log.warning(json.dumps({"event": "memory_model_rejected", "repo": repo, "names": bad}))
        return template, TEMPLATE
    return text, name
