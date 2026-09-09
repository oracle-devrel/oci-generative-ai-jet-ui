"""Idea & repurposing agent — suggests what to make next and how to repurpose what you've made,
grounded in YOUR brain: the consolidated facts the research agent has learned (themes, formats,
audience, gaps), your compiled wiki topics, and your recent content. A second showcase agent that
reads the same one database.

  cd oracle/agent && ../../.venv/bin/python idea_agent.py
"""
import json

import anthropic

import llm
from db import connect          # importing db loads oracle/.env
from content import list_topics

SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "new_ideas": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "properties": {
                "title": {"type": "string"},
                "angle": {"type": "string"},
                "format": {"type": "string"},
                "builds_on": {"type": "string"},
                "why": {"type": "string"},
            }, "required": ["title", "angle", "format", "builds_on", "why"]}},
        "repurpose": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "properties": {
                "from_topic": {"type": "string"},
                "into": {"type": "string"},
                "idea": {"type": "string"},
            }, "required": ["from_topic", "into", "idea"]}},
    },
    "required": ["new_ideas", "repurpose"],
}

SYSTEM = (
    "You are a content strategist for a tech creator. From what they've ALREADY covered (learned "
    "facts, wiki topics, recent titles), propose grounded NEXT ideas and ways to repurpose "
    "existing work. Lean into their recurring themes and especially their GAPS. Every suggestion "
    "must connect to something they've actually done — name it in builds_on / from_topic. Be "
    "specific and realistic to their formats; no generic advice."
)


def suggest(client, conn, n=6):
    cur = conn.cursor()
    cur.execute("SELECT category, fact FROM semantic_memory")
    facts = cur.fetchall()
    # content scope only — private/business titles must never reach an LLM prompt
    cur.execute("SELECT title FROM posts WHERE title IS NOT NULL "
                "AND NVL(visibility,'content') = 'content' ORDER BY published_at DESC "
                "FETCH FIRST 40 ROWS ONLY")
    recent = [r[0] for r in cur.fetchall()]
    topics = list_topics(conn)

    prompt = (
        "LEARNED FACTS (category | fact):\n" + "\n".join(f"- {c} | {f}" for c, f in facts) +
        "\n\nWIKI TOPICS:\n" + "\n".join(f"- {t}" for t in topics) +
        "\n\nRECENT CONTENT:\n" + "\n".join(f"- {t}" for t in recent) +
        f"\n\nPropose {n} new content ideas and 3-4 repurposing moves."
    )
    return llm.structured(SYSTEM, prompt, SCHEMA, max_tokens=4096)


def main():
    client = anthropic.Anthropic()
    conn = connect()
    try:
        out = suggest(client, conn)
        print("=== NEW IDEAS ===")
        for i in out["new_ideas"]:
            print(f"\n• {i['title']}  [{i['format']}]")
            print(f"    angle: {i['angle']}")
            print(f"    builds on: {i['builds_on']}")
            print(f"    why: {i['why']}")
        print("\n=== REPURPOSE ===")
        for r in out["repurpose"]:
            print(f"• {r['from_topic']} → {r['into']}: {r['idea']}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
