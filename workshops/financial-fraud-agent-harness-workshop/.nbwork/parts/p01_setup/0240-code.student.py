# TODO 1: ask the bare model a question about Meridian Bank data (no memory, retrieval or tools).
#   Steps:
#   1. Set QUESTION to something only the bank's data can answer (a customer, account or alert).
#   2. Run the cell: chat() sends it as the only message.
#   3. Read the answer and note what the model cannot know.
#   Guide: docs/part-1-setup.md#todo-1-question

QUESTION = ""

_bare_answer = chat([{"role": "user", "content": QUESTION}]).choices[0].message.content if QUESTION.strip() else None
print("A:", (_bare_answer or "")[:300])

# Hard-stop checkpoint: TODO 1
from workshop.llm import check_bare_question
check_bare_question(QUESTION, _bare_answer)
