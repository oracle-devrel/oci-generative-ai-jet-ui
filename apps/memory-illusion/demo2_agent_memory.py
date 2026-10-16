"""DEMO 2 — The same conversation through ORACLE AGENT MEMORY.

Raw messages go into Oracle AI Database. Before every turn we ask the memory
layer for a compact CONTEXT CARD (summary + relevant extracted facts) and send
ONLY that + the new question to the model. The token bar stays flat.

At the end we look INSIDE the database: the extracted memories — your
"Memory updated" moment — are just rows you can SELECT.

Run:  ./.venv/bin/python demo2_agent_memory.py
"""

import litellm
import oracledb
import ui
from config import (
    AGENT_ID,
    CHAT_MODEL,
    EMBED_DIM,
    EMBED_MODEL,
    MAX_TOKENS,
    OLLAMA_BASE,
    ORACLE_DSN,
    ORACLE_PASSWORD,
    ORACLE_USER,
    SYSTEM_PROMPT,
    TEMPERATURE,
    USER_ID,
    payload_tokens,
)
from conversation import SCRIPT
from oracleagentmemory.apis import Message
from oracleagentmemory.core import (
    MemoryExtractionConfig,
    MemoryExtractionMode,
    OracleAgentMemory,
    SchemaPolicy,
)
from oracleagentmemory.core.embedders.embedder import Embedder
from oracleagentmemory.core.llms.llm import Llm

litellm.suppress_debug_info = True

THREAD_ID = "tokyo_trip_demo"

# The extraction policy — the "remember better, not more" idea from Oracle's
# custom-memory-extraction blog. Applied to every extraction call.
EXTRACTION_POLICY = """
Extract only durable facts about the USER and their travel companions:
dietary restrictions, allergies, seating and travel preferences, budget,
trip plans, and names of companions. Allergies and dietary restrictions are
the highest-priority facts — record them exactly as stated, word for word.
Keep each memory short and specific.
Attribute every fact to the correct person — the user vs. a named companion —
and never merge two people's traits into one statement.
Ignore generic travel advice given by the assistant, greetings, small talk,
and anything already extracted. Never invent facts that were not stated.
""".strip()


def chat(messages: list[dict]) -> str:
    resp = litellm.completion(
        model=CHAT_MODEL,
        api_base=OLLAMA_BASE,
        messages=messages,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
    )
    return resp.choices[0].message.content or ""


def build_memory() -> OracleAgentMemory:
    pool = oracledb.create_pool(
        user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=ORACLE_DSN, min=1, max=4
    )
    return OracleAgentMemory(
        connection=pool,
        embedder=Embedder(model=EMBED_MODEL, api_base=OLLAMA_BASE, embedding_dimension=EMBED_DIM),
        llm=Llm(model=CHAT_MODEL, api_base=OLLAMA_BASE, temperature=0.0, max_tokens=1024, seed=42),
        schema_policy=SchemaPolicy.CREATE_IF_NECESSARY,
        memory_extraction_config=MemoryExtractionConfig(
            extract_memories=True,
            enable_context_summary=True,
            memory_extraction_frequency=2,  # small batches keep the 8B extractor grounded
            extraction_mode=MemoryExtractionMode.INLINE,
            memory_extraction_custom_instructions=EXTRACTION_POLICY,
        ),
    )


def main():
    ui.banner(
        "DEMO 2 — ORACLE AGENT MEMORY (database-backed memory layer)",
        "raw history lives in the database · the model gets a compact context card",
        "green",
    )

    memory = build_memory()

    # fresh run every time so the on-camera result is reproducible:
    # drop the thread AND any user-scoped memories from previous takes
    try:
        memory.delete_thread(THREAD_ID)
    except Exception:
        pass
    for r in memory.search(
        "anything",
        user_id=USER_ID,
        max_results=100,
        record_types=["memory", "fact", "preference", "guideline"],
    ):
        try:
            memory.delete_memory(r.id)
        except Exception:
            pass

    thread = memory.create_thread(
        thread_id=THREAD_ID, user_id=USER_ID, agent_id=AGENT_ID, context_card_token_limit=350
    )  # keep the card lean

    per_turn = []
    for turn, question in enumerate(SCRIPT, start=1):
        thread.add_messages([Message(role="user", content=question)])

        # bounded, prompt-ready state from the memory layer — NOT the transcript
        card = thread.get_context_card(max_recent_messages=2, max_relevant_results=6)
        context = card.formatted_content or ""

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT + "\n\n--- MEMORY CONTEXT (from database) ---\n" + context,
            },
            {"role": "user", "content": question},
        ]

        tokens = payload_tokens(messages)  # <-- what THIS request costs
        per_turn.append(tokens)

        ui.turn_header(turn, question)
        ui.token_row(
            "sent in this request",
            tokens,
            "green",
            extra="context card + question — transcript stays in the DB",
        )

        answer = chat(messages)
        ui.assistant_reply(answer)

        thread.add_messages([Message(role="assistant", content=answer)])

    memory.wait_for_memory_extraction()
    ui.totals("ORACLE AGENT MEMORY", per_turn, "green")
    ui.save_log("memory_log.json", per_turn)

    # ---- the "Memory updated" reveal: what got written to the database ----
    ui.console.print(
        "\n[bold]🧠 Durable memories the extraction LLM wrote to Oracle (SELECT-able rows):[/]\n"
    )
    results = memory.search(
        "user preferences, dietary restrictions, travel facts",
        user_id=USER_ID,
        max_results=12,
        record_types=["memory", "fact", "preference"],
    )
    seen = set()
    for r in results:
        key = r.content.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        rtype = getattr(r.record, "record_type", None) or type(r.record).__name__
        ui.console.print(f"   [green]▸[/] [bold]{rtype}[/]  {r.content}")
    if not results:
        ui.console.print(
            "   [dim](no extracted memories found — check the extraction LLM output)[/]"
        )

    memory.close()


if __name__ == "__main__":
    main()
