# Hard-stop checkpoint: TODO 2
# Test the recall_memories you just wrote: save one fact about a column, then search for it
# with words the fact doesn't contain. It should still come back, because the search is by meaning.
from workshop.memory import check_recall_memories
_subject = "FINANCE.TRANSACTIONS.AMOUNT_CENTS"
_query = "monetary denomination scale"
check_recall_memories(recall_memories, memory_client, USER_ID, AGENT_ID, _subject, _query)
