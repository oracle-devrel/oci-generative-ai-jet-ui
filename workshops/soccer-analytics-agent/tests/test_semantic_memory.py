import pytest
from soccer_agent.memory.semantic import SemanticMemory, Fact
from soccer_agent.agent.embeddings import embed_one
from soccer_agent.db import get_connection


@pytest.mark.integration
def test_upsert_and_search(memory_schema_ready, onnx_model_loaded):
    sm = SemanticMemory()
    with get_connection() as conn:
        conn.cursor().execute("DELETE FROM semantic_memory")
        conn.commit()

    spain_text = "Spain national football team tiki-taka short passing era 2008 2010 2012"
    brazil_text = "Brazil national football team joga bonito samba flair 1970"
    sm.upsert(Fact(fact_type="team_profile", subject_key="Spain",
                   summary=spain_text, source={"era": "2008-2012"},
                   embedding=embed_one(spain_text)))
    sm.upsert(Fact(fact_type="team_profile", subject_key="Brazil",
                   summary=brazil_text, source={"era": "1970"},
                   embedding=embed_one(brazil_text)))

    results = sm.search(
        embed_one("Spain dominant short passing tiki-taka"), limit=1,
    )
    assert len(results) == 1
    assert results[0].subject_key == "Spain"
