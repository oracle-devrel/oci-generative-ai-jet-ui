# TODO 1: ask the bare model a question about Meridian Bank data (no memory, retrieval or tools).

QUESTION = "Which Meridian Bank customer has the most flagged transactions in the last 30 days?"

_bare_answer = chat([{"role": "user", "content": QUESTION}]).choices[0].message.content if QUESTION.strip() else None
print("A:", (_bare_answer or "")[:300])

# Hard-stop checkpoint: TODO 1
from workshop.llm import check_bare_question
check_bare_question(QUESTION, _bare_answer)
