from langchain_oracledb import OracleEmbeddings, OracleVS
from langchain_oracledb.vectorstores.utils import DistanceStrategy
from workshop.retrieval import sync_knowledge

lc_embed = OracleEmbeddings(conn=agent_conn,
                            params={"provider": "database", "model": ONNX_EMBED_MODEL})
knowledge_vs = OracleVS(agent_conn, lc_embed, "AML_KNOWLEDGE_VS", DistanceStrategy.COSINE,
                        mutate_on_duplicate=True)
notes, memories = sync_knowledge(knowledge_vs, memory_client, USER_ID, AGENT_ID)
print(f"AML_KNOWLEDGE_VS: {notes} AML notes + {memories} OAMP memories")
