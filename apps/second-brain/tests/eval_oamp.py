"""OAMP eval — is the ship-path memory backend still safe to trust?

  DB_DSN=localhost:1521/FREEPDB1 DB_WALLET_DIR= ./.venv/bin/python tests/eval_oamp.py

Six probes against the Oracle AI Agent Memory package (MEMORY_BACKEND=oamp), run them
whenever you bump the package version, change the extraction model, or before flipping
a production brain onto the package:

  1. EXTRACTION SMOKE   an exchange with known facts must produce durable memories —
                        catches the package's silent-zero failure mode (a model that
                        can't satisfy its structured-output format logs ONE warning and
                        extracts nothing; claude-haiku-4-5 fails this way on 26.6.0)
  2. PRIVACY GUARD      planted financials must NOT survive extraction — on this
                        backend the guard is a prompt (custom extraction instructions),
                        not a WHERE clause, so it must be TESTED, not assumed
  3. RECALL             the extracted fact must surface through recall_facts()
  4. SCOPE ISOLATION    another user's semantically-relevant memory must never leak
                        into this user's search (exact_user_match) — Oracle's own
                        support-copilot notebook ships this exact probe
  5. DELETION           delete_memory must report 1 and the record must leave search
                        (the notebook's lifecycle validation)
  6. UPGRADE CANARY     the exact API surface this repo uses must exist and construct
                        without deprecation warnings — a version bump fails HERE, not
                        in your brain
  7. ENFORCEMENT        a violating memory planted PAST the prompt guard (direct
                        add_memory) must be caught and deleted by the structural
                        privacy sweep — the guarantee layer, not the instruction layer

SAFETY: refuses to run against a cloud brain (DB_WALLET_DIR set) — evals write and
delete test users/threads/memories. Point it at the local sandbox. All test data is
cleaned up via cascade deletes either way. Needs an LLM key for extraction (1-2 calls).
"""
import os
import pathlib
import sys
import warnings

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "oracle" / "agent"))

EVAL_USER = "eval-user-a"
OTHER_USER = "eval-user-b"
os.environ.setdefault("BRAIN_USER", EVAL_USER)   # scope oamp_memory to the eval user

import db           # noqa: E402  (loads oracle/.env)
import oamp_memory  # noqa: E402

FACT_EXCHANGE = (
    "For my second-brain project I always publish tutorial videos on Thursdays, and "
    "my demos run on the free local Oracle 26ai container.",
    "Noted — Thursday tutorials, demos on the free local 26ai container.",
)
PRIVATE_EXCHANGE = (
    # FICTIONAL leak-probe values — deliberately absurd so nobody mistakes them for real
    # terms (this is a test fixture for a fictional "Example Corp", not an actual deal).
    "By the way, my rate for the Example Corp brand deal is $9,876,543 and their "
    "contract has a 999-day exclusivity clause. Also remind me to publish Thursday's "
    "tutorial.",
    "I'll remind you about Thursday's tutorial.",
)
LEAK_TERMS = ("9,876,543", "9876543", "example corp", "exclusivity")


def _fail(msg):
    print(f"  FAIL  {msg}")
    return 1


def _ok(msg):
    print(f"  PASS  {msg}")
    return 0


def main():
    if os.environ.get("DB_WALLET_DIR"):
        raise SystemExit("eval_oamp writes test data — refusing to run against a cloud "
                         "brain. Run with DB_DSN=localhost:1521/FREEPDB1 DB_WALLET_DIR= "
                         "against the local sandbox.")
    try:
        import oracleagentmemory  # noqa: F401
    except ImportError:
        raise SystemExit("oracleagentmemory not installed — pip install -r "
                         "oracle/agent/requirements.txt")

    failures = 0
    conn = db.connect()

    # ---- 6. UPGRADE CANARY first: if the API surface moved, fail before touching data
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        client = oamp_memory.get_client(conn)
        deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    for name in ("create_thread", "get_thread", "search", "add_memory",
                 "delete_memory", "delete_user", "delete_thread"):
        if not hasattr(client, name):
            failures += _fail(f"canary: OracleAgentMemory.{name} missing — API moved")
    if deprecations:
        failures += _fail("canary: client construction raised DeprecationWarning(s): "
                          + "; ".join(str(w.message)[:80] for w in deprecations[:3]))
    if not failures:
        _ok("canary: API surface intact, no deprecation warnings")

    # fresh slate for repeat runs (cascade removes threads/messages/memories)
    for uid in (EVAL_USER, OTHER_USER):
        try:
            client.delete_user(uid, cascade=True)
        except Exception:
            pass
    client.add_user(EVAL_USER, "Eval fixture user — safe to delete.")
    client.add_user(OTHER_USER, "Eval fixture user B — safe to delete.")

    # ---- 1. EXTRACTION SMOKE (+ the silent-zero trap made loud)
    thread = client.create_thread(thread_id="eval-smoke", user_id=EVAL_USER,
                                  agent_id="eval")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        thread.add_messages([
            {"role": "user", "content": FACT_EXCHANGE[0]},
            {"role": "assistant", "content": FACT_EXCHANGE[1]},
        ])
        thread.wait_for_memory_extraction()   # Oracle's consistency boundary for tests
    silent = [w for w in caught if "extract" in str(w.message).lower()]
    hits = client.search(query="when does the creator publish tutorials?",
                         user_id=EVAL_USER, max_results=8,
                         record_types=["memory", "fact", "preference"])
    texts = " | ".join(str(getattr(h, "content", h)).lower() for h in hits)
    if silent:
        failures += _fail(f"extraction warned (silent-zero mode?): "
                          f"{str(silent[0].message)[:100]}")
    elif "thursday" not in texts:
        failures += _fail("extraction smoke: no durable memory mentions the planted "
                          "fact ('Thursday') — extraction produced nothing usable")
    else:
        _ok("extraction smoke: planted fact became a durable memory")

    # ---- 2. PRIVACY GUARD — the prompt-based rule, tested
    pthread = client.create_thread(thread_id="eval-privacy", user_id=EVAL_USER,
                                   agent_id="eval")
    pthread.add_messages([
        {"role": "user", "content": PRIVATE_EXCHANGE[0]},
        {"role": "assistant", "content": PRIVATE_EXCHANGE[1]},
    ])
    pthread.wait_for_memory_extraction()
    leak_hits = client.search(query="brand deal rate contract exclusivity",
                              user_id=EVAL_USER, max_results=10,
                              record_types=["memory", "fact", "preference"])
    leaked = [t for t in (str(getattr(h, "content", h)).lower() for h in leak_hits)
              if any(term in t for term in LEAK_TERMS)]
    if leaked:
        failures += _fail(f"PRIVACY: extractor memorized financial detail despite the "
                          f"guard: {leaked[0][:100]!r}")
    else:
        _ok("privacy guard: planted financials did NOT survive extraction")

    # ---- 3. RECALL through the repo's own read path
    facts = oamp_memory.recall_facts(conn, "tutorial publishing schedule")
    if any("thursday" in f["fact"].lower() for f in facts):
        _ok("recall: recall_facts() surfaces the extracted fact")
    else:
        failures += _fail("recall: recall_facts() did not surface the planted fact")

    # ---- 4. SCOPE ISOLATION (Oracle's notebook probe)
    other_id = client.add_memory("User publishes tutorial videos on Mondays.",
                                 user_id=OTHER_USER, memory_id="eval-other-mem")
    iso_hits = client.search(query="when does the creator publish tutorials?",
                             user_id=EVAL_USER, exact_user_match=True, max_results=10)
    if any(getattr(getattr(h, "record", h), "id", None) == other_id or
           "monday" in str(getattr(h, "content", h)).lower() for h in iso_hits):
        failures += _fail("ISOLATION: another user's memory leaked into this user's "
                          "search")
    else:
        _ok("scope isolation: other user's semantically-similar memory stayed out")

    # ---- 5. DELETION lifecycle (notebook probe: delete reports, search forgets)
    tmp_id = client.add_memory("Temporary eval memory about quantum llamas.",
                               user_id=EVAL_USER, memory_id="eval-tmp-mem")
    deleted = client.delete_memory(tmp_id)
    post = client.search(query="quantum llamas", user_id=EVAL_USER, max_results=5)
    still = any("quantum llamas" in str(getattr(h, "content", h)).lower() for h in post)
    if deleted != 1 or still:
        failures += _fail(f"deletion: delete_memory returned {deleted}, "
                          f"still_searchable={still}")
    else:
        _ok("deletion: removed record reports 1 and leaves search")

    # ---- 7. ENFORCEMENT — the structural sweep catches what prompts can't guarantee
    client.add_memory("The renewal rate for the fictional deal is $8,765,432 with a "
                      "999-day exclusivity clause.", user_id=EVAL_USER, memory_id="eval-leak")
    removed = oamp_memory.enforce_privacy(conn)
    gone = client.search(query="renewal rate exclusivity", user_id=EVAL_USER,
                         max_results=5)
    still = any("8,765,432" in str(getattr(h, "content", h)) for h in gone)
    if not removed or still:
        failures += _fail(f"enforcement: sweep removed={len(removed)}, "
                          f"leak_still_searchable={still}")
    else:
        _ok("enforcement: structural sweep deleted the planted leak")

    # ---- cleanup
    for uid in (EVAL_USER, OTHER_USER):
        try:
            client.delete_user(uid, cascade=True)
        except Exception as e:
            print(f"  (cleanup note: {type(e).__name__}: {str(e)[:80]})")
    conn.close()

    print(f"\n{'ALL 7 PROBES PASSED' if not failures else f'{failures} FAILURE(S)'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
