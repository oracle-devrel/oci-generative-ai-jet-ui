"""Tests for ResponseCache."""

import time

import pytest

from agent_reasoning.cache import ResponseCache


class TestResponseCache:
    def test_put_and_get(self):
        cache = ResponseCache()
        cache.put("gemma3", "cot", "What is 2+2?", "4")
        assert cache.get("gemma3", "cot", "What is 2+2?") == "4"

    def test_cache_miss(self):
        cache = ResponseCache()
        assert cache.get("gemma3", "cot", "unknown query") is None

    def test_different_strategies_different_keys(self):
        cache = ResponseCache()
        cache.put("gemma3", "cot", "query", "cot response")
        cache.put("gemma3", "tot", "query", "tot response")
        assert cache.get("gemma3", "cot", "query") == "cot response"
        assert cache.get("gemma3", "tot", "query") == "tot response"

    def test_ttl_expiration(self):
        cache = ResponseCache(ttl=0.1)
        cache.put("m", "s", "q", "response")
        assert cache.get("m", "s", "q") == "response"
        time.sleep(0.15)
        assert cache.get("m", "s", "q") is None

    def test_max_size_eviction(self):
        cache = ResponseCache(max_size=2)
        cache.put("m", "s", "q1", "r1")
        cache.put("m", "s", "q2", "r2")
        cache.put("m", "s", "q3", "r3")
        # Oldest (q1) should be evicted
        assert cache.get("m", "s", "q1") is None
        assert cache.get("m", "s", "q2") == "r2"
        assert cache.get("m", "s", "q3") == "r3"

    def test_disabled_cache(self):
        cache = ResponseCache(enabled=False)
        cache.put("m", "s", "q", "r")
        assert cache.get("m", "s", "q") is None

    def test_clear(self):
        cache = ResponseCache()
        cache.put("m", "s", "q", "r")
        cache.clear()
        assert cache.get("m", "s", "q") is None

    def test_stats(self):
        cache = ResponseCache()
        cache.put("m", "s", "q", "r")
        cache.get("m", "s", "q")  # hit
        cache.get("m", "s", "miss")  # miss
        stats = cache.stats
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1
        assert stats["hit_rate"] == 0.5

    def test_thread_safety(self):
        """Concurrent access should not corrupt state."""
        import threading

        cache = ResponseCache(max_size=100)
        errors = []

        def writer(tid):
            try:
                for i in range(50):
                    cache.put("m", "s", f"q-{tid}-{i}", f"r-{tid}-{i}")
            except Exception as e:
                errors.append(e)

        def reader(tid):
            try:
                for i in range(50):
                    cache.get("m", "s", f"q-{tid}-{i}")
            except Exception as e:
                errors.append(e)

        threads = []
        for t in range(4):
            threads.append(threading.Thread(target=writer, args=(t,)))
            threads.append(threading.Thread(target=reader, args=(t,)))
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0
        assert cache.stats["size"] <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
