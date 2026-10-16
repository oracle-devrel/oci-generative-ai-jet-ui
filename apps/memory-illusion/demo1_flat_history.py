"""DEMO 1 — The way (almost) every chat app works today: FLAT HISTORY.

Every turn re-sends the ENTIRE conversation to the model.
Watch the token bar grow — you are paying to re-read turn 1, again and again.

Run:  ./.venv/bin/python demo1_flat_history.py
"""

import litellm
import ui
from config import CHAT_MODEL, MAX_TOKENS, OLLAMA_BASE, SYSTEM_PROMPT, TEMPERATURE, payload_tokens
from conversation import SCRIPT

litellm.suppress_debug_info = True


def chat(messages: list[dict]) -> str:
    resp = litellm.completion(
        model=CHAT_MODEL,
        api_base=OLLAMA_BASE,
        messages=messages,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
    )
    return resp.choices[0].message.content or ""


def main():
    ui.banner(
        "DEMO 1 — FLAT HISTORY (no memory layer)",
        "the entire conversation is re-sent on every single request",
        "red",
    )

    history = [{"role": "system", "content": SYSTEM_PROMPT}]
    per_turn = []

    for turn, question in enumerate(SCRIPT, start=1):
        history.append({"role": "user", "content": question})

        tokens = payload_tokens(history)  # <-- what THIS request costs
        per_turn.append(tokens)

        ui.turn_header(turn, question)
        ui.token_row(
            "sent in this request", tokens, "red", extra=f"{len(history)} messages re-uploaded"
        )

        answer = chat(history)
        ui.assistant_reply(answer)

        history.append({"role": "assistant", "content": answer})

    ui.totals("FLAT HISTORY", per_turn, "red")
    ui.save_log("flat_log.json", per_turn)


if __name__ == "__main__":
    main()
