import uuid
import pytest
from soccer_agent.memory.episodic import EpisodicMemory, Turn
from soccer_agent.agent.embeddings import embed_one


@pytest.mark.integration
def test_append_and_recent(memory_schema_ready, onnx_model_loaded):
    s = f"test-{uuid.uuid4()}"
    em = EpisodicMemory(s)
    em.append(Turn(role="user", content="Hello", embedding=embed_one("Hello")))
    em.append(Turn(role="assistant", content="Hi back", embedding=embed_one("Hi back")))
    turns = em.recent(10)
    assert [t.role for t in turns] == ["user", "assistant"]
    assert turns[0].content == "Hello"


@pytest.mark.integration
def test_vector_search(memory_schema_ready, onnx_model_loaded):
    s = f"test-{uuid.uuid4()}"
    em = EpisodicMemory(s)
    em.append(Turn(role="user", content="alpha", embedding=embed_one("alpha")))
    em.append(Turn(role="user", content="beta", embedding=embed_one("beta")))
    results = em.search(embed_one("alpha"), limit=1)
    assert len(results) == 1
    assert results[0].content == "alpha"
