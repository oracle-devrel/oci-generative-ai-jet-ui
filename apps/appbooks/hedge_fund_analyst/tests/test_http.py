import os

import httpx

BASE = os.environ.get("HF_BASE_URL", "http://127.0.0.1:8061")


def test_all_read_surfaces():
    with httpx.Client(base_url=BASE, timeout=60) as c:
        assert c.get("/").status_code == 200
        h = c.get("/api/health").json()
        assert h["ready"] and all(x["isolated"] for x in h["isolation"])
        assert {m["id"] for m in h["models"] if m["enabled"]} >= {"ollama"}
        for persona in ["Credit", "Markets"]:
            for path in [
                "/api/data/tables",
                "/api/graph",
                "/api/memory",
                "/api/sql",
                "/api/vectors?q=rate+risk",
                "/api/data/hf_semantics",
                "/api/data/hf_golden",
                "/api/semcache",
            ]:
                r = c.get(path + ("&" if "?" in path else "?") + "persona=" + persona)
                assert r.status_code == 200, (path, r.text)
        assert c.get("/api/data/nope").status_code == 404
        assert c.get("/api/data/hf_positions?persona=Admin").status_code == 422
        assert c.get("/api/data/hf_positions?limit=1000").status_code == 422
        assert (
            c.post("/api/chat", json={"question": "hi", "model_id": "unknown"}).status_code == 409
        )
        assert c.get("/.env").status_code == 404
        assert set(c.get("/api/simulate/mixes").json()["mixes"]) == {"golden", "repeat", "numeric"}
        assert (
            c.post("/api/simulate", json={"turns": 0}).status_code == 422
            and c.post("/api/simulate", json={"turns": 51}).status_code == 422
        )
        tc = [x for x in h["components"] if x["component"] == "true_cache"][0]
        assert tc["state"] in ("running", "not running") and (
            "PHYSICAL STANDBY" in tc["detail"] or tc["state"] == "not running"
        )
