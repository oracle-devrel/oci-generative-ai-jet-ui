from workshop.retrieval import prepare_search
rerank, write_facts = prepare_search(agent_conn, knowledge_vs, scanner, memory_client, USER_ID, AGENT_ID)
