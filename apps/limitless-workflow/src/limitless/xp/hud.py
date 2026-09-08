from __future__ import annotations


def _phase_label(phase: str) -> str:
    return f"{phase.replace('-', ' ').title()} Phase"


def build_status_hud(
    *,
    topic_title: str,
    phase: str,
    target_concept: str | None,
    hints_used: int,
    concepts_covered: int,
    grounding_label: str | None,
) -> str:
    header = f"[Limitless XP Builder | {topic_title} | {_phase_label(phase)} | {target_concept or '-'}]"
    lines = [header]
    if grounding_label:
        lines.append(f"|- grounded in: {grounding_label}")
    lines.extend([
        "|- reply normally to continue",
        "   commands: /hint | /status | /finish",
        f"   hints used: {hints_used}",
        f"   concepts covered: {concepts_covered}",
    ])
    return "\n".join(lines)
