"""AML triage replay — the desk's morning, re-driven from a real captured run.

The workshop cannot spend live Grok tokens on an autonomous AML loop, so this
module replays ONE genuine run (`agent/aml_capture.py`, notebook §6.3-6.4)
step by step over Socket.IO, wall-clock scaled by `AML_REPLAY_SPEED`, and
records every decision in AGENT.AML_REPLAY.

The queue is never hardcoded. It is the notebook's §6.1 aggregation run against
the live FINANCE schema — one row per (customer, AML typology), newest activity
first — so the desk keeps working whatever the live feed just inserted. Alerts
whose (customer_id, typology) has a capture replay that capture verbatim; every
other alert emits the harness's documented fallback (REVIEW_REQUIRED, routed to
a human) and is labelled `mode: "fallback"` on the wire, so a replayed decision
is never presented as model output — and model text is never invented.

Socket events, client to server: `aml_status_request`, `aml_sweep_run`,
`aml_clear`, `aml_recall_run`. Server to client: `aml_status`, `aml_queue`,
`aml_sweep_started`, `aml_alert_started`, `aml_step`, `aml_step_finished`,
`aml_alert_decided`, `aml_alert_recorded`, `aml_sweep_finished`,
`aml_recall_started`, `aml_recall_finished`. These payload shapes are the
front-end contract — the AML desk panel consumes them as they are, so field
names here are not free to drift. Sweep and recall traffic is broadcast (the
desk is one shared screen) while status and queue replies go to the requesting
socket.

Writes are confined to AGENT.AML_REPLAY. AGENT.AML_TRIAGE holds the genuine
capture and is never touched.
"""

from __future__ import annotations

import os
import threading
import time
import uuid
from datetime import datetime, timezone

from flask import request as flask_request

from agent import aml_capture
from config import DEMO_USER
from db.connection import connect_agent


# Wall-clock multiplier for every captured step: 1 = real time, 0.02 = a sweep
# in seconds. Reported in `aml_status` so the UI can say how fast it is running.
SPEED = float(os.environ.get("AML_REPLAY_SPEED", "1"))

LOOKBACK_DAYS = 30          # the alert window the notebook's §6.1 queue uses
DEFAULT_LIMIT = 3           # alerts per sweep, mirroring TRIAGE_LIMIT
MAX_LIMIT = 12              # keep one sweep bounded regardless of what the client asks
CONTEXT_MS = 400            # the evidence pack has no capture; this is its nominal cost

# Work the alerts we have a captured decision for first (see `_alert_queue`).
# The replay has no live model, so an alert without a capture can only become
# the harness's REVIEW_REQUIRED path; preferring captures keeps a demo sweep
# showing real decisions. Set AML_QUEUE_PREFER_CAPTURE=false for pure recency.
PREFER_CAPTURE = os.environ.get("AML_QUEUE_PREFER_CAPTURE", "true").strip().lower() in ("1", "true", "yes", "on")

# The two steps every uncaptured alert replays. They are the shape of the
# captured runs, not a claim about a model call that happened: see _fallback_steps.
FALLBACK_SEARCH_MS = 6200
FALLBACK_MODEL_MS = 23000
FALLBACK_SEARCH_TOOL = "search_knowledge"

# Presentation labels the front-end contract fixes. The model name is
# aml_capture.MODEL ("xai.grok-4.3 (OCI GenAI)"); the step label uses the short form.
MODEL_LABEL = "model call · xai.grok-4.3"
FALLBACK_MODEL_LABEL = "model call · not captured"
CONTEXT_LABEL = "evidence pack · assembled from FINANCE"

# The harness's own fallback (notebook §6.2): the decision vocabulary and the
# wording a REVIEW_REQUIRED row carries when no validated model reply exists.
FALLBACK_DECISION = {
    "decision": "REVIEW_REQUIRED",
    "confidence": 0.0,
    "rationale": "No validated model reply captured for this alert — routed to a human reviewer.",
    "recommended_next_action": "Human review of the alert.",
}

# Same rule texts the notebook's §6.2 evidence pack prints under RULE.
TYPOGRAPHY = {
    "STRUCTURING": "$10,000 CTR threshold - deposits split just under it, repeated in a short window.",
    "GEO_VELOCITY": "Impossible travel - one card, far-apart regions, hours apart (card cloning / takeover).",
    "HIGH_RISK_COUNTRY": "Wires to elevated-risk corridors (crypto, gold & forex, casinos, remittance) after an inbound credit.",
    "RAPID_CASH_OUT": "Large inbound wire, then rapid ATM withdrawals draining the account within ~48 hours.",
    "LARGE_CASH_DEPOSIT": "A single cash deposit above $50,000 with no plausible source of funds.",
}

LEDGER_TABLE = "AML_REPLAY"
# "mode" is quoted because MODE is reserved as of Oracle 23ai; the column keeps
# the name the front-end contract's ledger rows use.
LEDGER_DDL = (
    "CREATE TABLE aml_replay ("
    "  run_id         VARCHAR2(32),"
    "  replayed_at    TIMESTAMP,"
    "  customer_id    NUMBER,"
    "  customer_name  VARCHAR2(120),"
    "  typology       VARCHAR2(60),"
    "  risk_rating    NUMBER,"
    "  flagged_txns   NUMBER,"
    "  exposure_cents NUMBER,"
    "  decision       VARCHAR2(20),"
    "  confidence     NUMBER(4,2),"
    "  rationale      VARCHAR2(1000),"
    "  next_action    VARCHAR2(400),"
    "  sar_reason     VARCHAR2(60),"
    '  "mode"         VARCHAR2(12),'
    "  elapsed_ms     NUMBER,"
    "  tokens         NUMBER)"
)

ALERT_QUEUE_SQL = f"""
WITH flagged AS (
  SELECT a.customer_id, t.flag_reason, t.txn_id, t.txn_ts, t.amount_cents, t.channel, t.status
    FROM {DEMO_USER}.transactions t
    JOIN {DEMO_USER}.accounts a ON a.account_id = t.account_id
   WHERE t.status IN ('FLAGGED','BLOCKED') AND t.flag_reason IS NOT NULL
     AND t.txn_ts >= SYSTIMESTAMP - NUMTODSINTERVAL(:days, 'DAY')
     {{customer_filter}}
)
SELECT f.customer_id, cu.full_name, cu.segment, cu.country, cu.risk_rating,
       f.flag_reason AS typology,
       COUNT(*) AS flagged_txns,
       SUM(f.amount_cents) AS exposure_cents,
       MIN(f.txn_ts) AS window_start, MAX(f.txn_ts) AS window_end,
       COUNT(DISTINCT f.channel) AS channels,
       SUM(CASE WHEN f.status = 'BLOCKED' THEN 1 ELSE 0 END) AS blocked_txns,
       (SELECT COUNT(*) FROM {DEMO_USER}.sar_reports s WHERE s.customer_id = f.customer_id) AS prior_sars
  FROM flagged f
  JOIN {DEMO_USER}.customers cu ON cu.customer_id = f.customer_id
 GROUP BY f.customer_id, cu.full_name, cu.segment, cu.country, cu.risk_rating, f.flag_reason
 ORDER BY MAX(f.txn_ts) DESC
 {{fetch_first}}
"""

QUEUE_FETCH = 40            # rows the generic pass pulls before the merge

# (customer_id, typology) -> the captured run that alert replays.
CAPTURED = {(run["customer_id"], run["typology"]): run for run in aml_capture.RUNS}

# Real OS threads (Socket.IO threading mode): socket handlers and the sweep task
# run concurrently, so claims on `running`/`recalling` and swaps of the
# connection are check-then-act sequences that `_LOCK` makes atomic.
_LOCK = threading.Lock()

_state: dict = {
    "socketio": None,
    "conn": None,
    "owns_conn": False,     # False while we are borrowing the app's agent connection
    "running": False,       # a sweep is in flight
    "recalling": False,     # §6.4's memory recall is in flight
    "last": None,           # the last finished sweep, for aml_status
}


# --------------------------------------------------------------------------- #
# Connection + helpers
# --------------------------------------------------------------------------- #

def _conn():
    with _LOCK:
        c = _state.get("conn")
        if c is None:
            c = connect_agent()
            _state["conn"] = c
            _state["owns_conn"] = True
        return c


def _reset_conn() -> None:
    """Forget our connection so the next call dials a fresh one. On boot the
    connection is the app's, shared with the chat path — we never close that one
    out from under it; we only close a connection this module opened itself."""
    with _LOCK:
        c = _state.get("conn")
        owned = _state.get("owns_conn")
        _state["conn"] = None
        _state["owns_conn"] = False
    if c is not None and owned:
        try:
            c.close()
        except Exception:
            pass


def _rows(sql: str, **binds) -> list[dict]:
    """Run SQL and return list[dict] with lowercased column names (notebook §6.1)."""
    with _conn().cursor() as cur:
        cur.execute(sql, **binds)
        cols = [d[0].lower() for d in cur.description]
        return [dict(zip(cols, row)) for row in cur]


def _money(cents) -> str:
    return f"${(cents or 0) / 100:,.2f}"


def _iso(value) -> str | None:
    return value.isoformat() if value is not None else None


def _emit(event: str, payload: dict) -> None:
    socketio = _state["socketio"]
    if socketio is not None:
        socketio.emit(event, payload)


def _sleep_ms(ms: int) -> None:
    """Sleep one captured step, scaled by AML_REPLAY_SPEED. Payloads always carry
    the captured duration — the scaled wall clock is never reported as the run's."""
    socketio = _state["socketio"]
    if socketio is not None:
        socketio.sleep(ms / 1000.0 * SPEED)


def _clamp_limit(value, default: int = DEFAULT_LIMIT) -> int:
    try:
        limit = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(MAX_LIMIT, limit))


# --------------------------------------------------------------------------- #
# The alert queue (§6.1, newest first)
# --------------------------------------------------------------------------- #

def _queue_alert(row: dict) -> dict:
    """One aggregated queue row as the alert dict the sweep and the UI use."""
    return {
        "customer_id": int(row["customer_id"]),
        "customer_name": row["full_name"],
        "segment": row["segment"],
        "country": row["country"],
        "risk_rating": int(row["risk_rating"]),
        "typology": row["typology"],
        "flagged_txns": int(row["flagged_txns"]),
        "exposure_cents": int(row["exposure_cents"]),
        "channels": int(row["channels"]),
        "blocked_txns": int(row["blocked_txns"]),
        "prior_sars": int(row["prior_sars"]),
        "window_start": row["window_start"],
        "window_end": row["window_end"],
        "capture": (int(row["customer_id"]), row["typology"]) in CAPTURED,
    }


def _alert_queue(limit: int = DEFAULT_LIMIT) -> list[dict]:
    """The alerts this sweep should work: every (customer, typology) group of
    FLAGGED / BLOCKED transactions in the last 30 days, `capture` set when the
    capture has a decision for that pair.

    Ordering is newest activity first — the desk starts where the live feed just
    left off — except that alerts with a captured decision are preferred within
    the same freshness window: the replay cannot call the model, so an alert it
    has no capture for can only be routed to a human (the harness's own
    REVIEW_REQUIRED policy). Preferring the captured ones keeps a demo sweep
    showing real decisions while the human-review path stays visible for
    everything else. `AML_QUEUE_PREFER_CAPTURE=false` restores plain recency.
    """
    # Fetch a wider window than the sweep needs: the capture-preferred ordering
    # happens here, and four captured pairs must be able to surface even on a
    # busy feed (the feed's spotlight keeps their groups fresh).
    fetch = max(limit * 8, QUEUE_FETCH)
    rows = _rows(
        ALERT_QUEUE_SQL.format(customer_filter="", fetch_first="FETCH FIRST :n ROWS ONLY"),
        days=LOOKBACK_DAYS, n=fetch,
    )
    alerts = [_queue_alert(row) for row in rows]
    if not PREFER_CAPTURE:
        return alerts[:limit]

    captured = [a for a in alerts if a["capture"]][:limit]
    # A captured pair whose group is older than the generic fetch window (the
    # seed carries rows timestamped later today, so recency alone can bury it)
    # is looked up directly: the capture is why this sweep exists.
    missing = sorted({cid for cid, _ in CAPTURED} - {a["customer_id"] for a in captured})
    if missing and len(captured) < limit:
        marks = ", ".join(f":c{i}" for i in range(len(missing)))
        binds = {f"c{i}": cid for i, cid in enumerate(missing)}
        rows = _rows(
            ALERT_QUEUE_SQL.format(
                customer_filter=f"AND a.customer_id IN ({marks})", fetch_first="",
            ),
            days=LOOKBACK_DAYS, **binds,
        )
        captured.extend(
            a for a in (_queue_alert(row) for row in rows)
            if a["capture"] and a["customer_id"] not in {c["customer_id"] for c in captured}
        )
    rest = [a for a in alerts if not a["capture"]]
    return (captured[:limit] + rest)[:limit]


def _alert_payload(alert: dict) -> dict:
    """The alert as the front-end contract defines it (timestamps as ISO strings)."""
    return {
        "customer_id": alert["customer_id"],
        "customer_name": alert["customer_name"],
        "typology": alert["typology"],
        "risk_rating": alert["risk_rating"],
        "flagged_txns": alert["flagged_txns"],
        "exposure_cents": alert["exposure_cents"],
        "blocked_txns": alert["blocked_txns"],
        "prior_sars": alert["prior_sars"],
        "window_start": _iso(alert["window_start"]),
        "window_end": _iso(alert["window_end"]),
        "capture": alert["capture"],
    }


def _queue_payload(alert: dict) -> dict:
    """The queue preview shape — the alert minus its window start."""
    payload = _alert_payload(alert)
    payload.pop("window_start")
    return payload


# --------------------------------------------------------------------------- #
# The evidence pack (§6.2)
# --------------------------------------------------------------------------- #

def evidence_pack(alert: dict, max_txns: int = 8) -> str:
    """Everything the agent is allowed to see about one alert. All of it from SQL
    and all of it scoped to the alert's own window, so the numbers the model
    reasoned over match the numbers in the header. Line labels are fixed — the UI
    shows them verbatim."""
    customer_id, typology = alert["customer_id"], alert["typology"]
    lines = [
        f"ALERT  customer {customer_id} | {alert['customer_name']} | {alert['segment']} | "
        f"{alert['country']} | risk_rating {alert['risk_rating']}/100",
        f"RULE   {typology} — {TYPOGRAPHY.get(typology, '')}",
        f"QUEUE  {alert['flagged_txns']} flagged txn(s), {_money(alert['exposure_cents'])} total, "
        f"{alert['window_start']:%Y-%m-%d} to {alert['window_end']:%Y-%m-%d}, "
        f"{alert['channels']} channel(s), {alert['blocked_txns']} blocked attempt(s)",
        "FLAGGED TRANSACTIONS IN THIS WINDOW (newest first; amounts in USD):",
    ]
    for t in _rows(f"""
            SELECT t.txn_id, TO_CHAR(t.txn_ts,'YYYY-MM-DD HH24:MI') AS seen_at, t.amount_cents,
                   t.channel, t.txn_type, t.status, t.region, m.name AS merchant
              FROM {DEMO_USER}.transactions t
              JOIN {DEMO_USER}.accounts a ON a.account_id = t.account_id
              LEFT JOIN {DEMO_USER}.merchants m ON m.merchant_id = t.merchant_id
             WHERE a.customer_id = :cid AND t.status IN ('FLAGGED','BLOCKED')
               AND t.flag_reason = :typo AND t.txn_ts >= :wstart
             ORDER BY t.txn_ts DESC FETCH FIRST :n ROWS ONLY""",
                 cid=customer_id, typo=typology, wstart=alert["window_start"], n=max_txns):
        lines.append(f"  txn {t['txn_id']:>5}  {t['seen_at']}  {_money(t['amount_cents']):>13}  "
                     f"{t['channel']}/{t['txn_type']}  status={t['status']}  "
                     f"region={t['region']}  merchant={t['merchant'] or '-'}")

    history = _rows(f"""
            SELECT COUNT(*) AS older_txns,
                   TO_CHAR(MIN(t.txn_ts),'YYYY-MM-DD') AS first_seen,
                   TO_CHAR(MAX(t.txn_ts),'YYYY-MM-DD') AS last_seen
              FROM {DEMO_USER}.transactions t
              JOIN {DEMO_USER}.accounts a ON a.account_id = t.account_id
             WHERE a.customer_id = :cid AND t.status IN ('FLAGGED','BLOCKED')
               AND (t.flag_reason <> :typo OR t.flag_reason IS NULL OR t.txn_ts < :wstart)""",
                     cid=customer_id, typo=typology, wstart=alert["window_start"])[0]
    if history["older_txns"]:
        lines.append(f"FLAGGED HISTORY (outside this window): {history['older_txns']} earlier flagged "
                     f"txn(s), {history['first_seen']} to {history['last_seen']} — context only; the "
                     f"window above is what this decision covers.")

    lines.append("RECENT ACTIVITY, ANY STATUS (top 6 by amount, last 30 days — this is the context a "
                 "single flagged row cannot carry):")
    for t in _rows(f"""
            SELECT t.txn_id, TO_CHAR(t.txn_ts,'YYYY-MM-DD HH24:MI') AS seen_at, t.amount_cents,
                   t.channel, t.txn_type, t.status, m.name AS merchant
              FROM {DEMO_USER}.transactions t
              JOIN {DEMO_USER}.accounts a ON a.account_id = t.account_id
              LEFT JOIN {DEMO_USER}.merchants m ON m.merchant_id = t.merchant_id
             WHERE a.customer_id = :cid AND t.txn_ts >= SYSTIMESTAMP - INTERVAL '30' DAY
             ORDER BY t.amount_cents DESC FETCH FIRST 6 ROWS ONLY""", cid=customer_id):
        lines.append(f"  txn {t['txn_id']:>5}  {t['seen_at']}  {_money(t['amount_cents']):>13}  "
                     f"{t['channel']}/{t['txn_type']}  status={t['status']}  "
                     f"merchant={t['merchant'] or '-'}")

    for a in _rows(f"""
            SELECT a.account_id, a.account_type, a.currency, a.balance_cents, b.city, b.region
              FROM {DEMO_USER}.accounts a JOIN {DEMO_USER}.branches b ON b.branch_id = a.branch_id
             WHERE a.customer_id = :cid ORDER BY a.opened_ts""", cid=customer_id):
        lines.append(f"ACCOUNT #{a['account_id']} {a['account_type']} {a['currency']} "
                     f"balance {_money(a['balance_cents'])} ({a['city']}, {a['region']})")

    flow = _rows(f"""
            SELECT SUM(CASE WHEN t.txn_type IN ('DEPOSIT','WIRE_IN') THEN t.amount_cents ELSE 0 END) AS money_in,
                   SUM(CASE WHEN t.txn_type IN ('WITHDRAWAL','WIRE_OUT') THEN t.amount_cents ELSE 0 END) AS money_out
              FROM {DEMO_USER}.transactions t JOIN {DEMO_USER}.accounts a ON a.account_id = t.account_id
             WHERE a.customer_id = :cid AND t.txn_ts >= SYSTIMESTAMP - INTERVAL '30' DAY""",
                 cid=customer_id)[0]
    lines.append(f"30-DAY FLOW: money-in {_money(flow['money_in'])} | money-out {_money(flow['money_out'])}")

    for s in _rows(f"""
            SELECT sar_id, reason_code, status, TO_CHAR(filed_ts,'YYYY-MM-DD') AS filed,
                   SUBSTR(narrative, 1, 180) AS narrative
              FROM {DEMO_USER}.sar_reports WHERE customer_id = :cid ORDER BY filed_ts DESC""",
                   cid=customer_id):
        lines.append(f"PRIOR SAR {s['sar_id']}: {s['reason_code']} status={s['status']} "
                     f"filed {s['filed']} — {s['narrative']}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# The ledger (AGENT.AML_REPLAY)
# --------------------------------------------------------------------------- #

def ensure_ledger(conn) -> None:
    """Create the replay ledger on first boot (idempotent), mirroring the
    notebook's §6.1 ledger cell. One row per alert per sweep; the genuine
    capture in AGENT.AML_TRIAGE is deliberately never written to."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM user_tables WHERE table_name = :1", [LEDGER_TABLE])
        if not cur.fetchone()[0]:
            cur.execute(LEDGER_DDL)
    conn.commit()


def _insert_ledger(run_id: str, row: dict, replayed_at: datetime) -> None:
    with _conn().cursor() as cur:
        cur.execute(
            "INSERT INTO aml_replay (run_id, replayed_at, customer_id, customer_name, typology,"
            " risk_rating, flagged_txns, exposure_cents, decision, confidence, rationale,"
            ' next_action, sar_reason, "mode", elapsed_ms, tokens)'
            " VALUES (:run_id, :replayed_at, :customer_id, :customer_name, :typology,"
            " :risk_rating, :flagged_txns, :exposure_cents, :decision, :confidence, :rationale,"
            " :next_action, :sar_reason, :run_mode, :elapsed_ms, :tokens)",
            run_id=run_id, replayed_at=replayed_at, customer_id=row["customer_id"],
            customer_name=row["customer_name"], typology=row["typology"],
            risk_rating=row["risk_rating"], flagged_txns=row["flagged_txns"],
            exposure_cents=row["exposure_cents"], decision=row["decision"],
            confidence=row["confidence"], rationale=row["rationale"],
            next_action=row["next_action"], sar_reason=row["sar_reason"],
            run_mode=row["mode"], elapsed_ms=row["elapsed_ms"], tokens=row["tokens"],
        )
    _conn().commit()


# --------------------------------------------------------------------------- #
# Working one alert
# --------------------------------------------------------------------------- #

def _captured_steps(run: dict) -> list[dict]:
    """The captured steps, in order, as the sweep replays them."""
    return [dict(step) for step in run["steps"]]


def _fallback_steps(alert: dict) -> list[dict]:
    """The two steps an uncaptured alert replays: the memory search the desk
    would have run, then the decision step. Nothing here is model output — the
    tokens stay 0, the labels say so, and the decision is the harness's own
    REVIEW_REQUIRED fallback."""
    return [
        {
            "kind": "tool",
            "tool": FALLBACK_SEARCH_TOOL,
            "args": {
                "query": f"{alert['customer_name']} {alert['customer_id']} "
                         f"{alert['typology']} alert decision prior SAR",
                "kinds": "episodic",
            },
            "duration_ms": FALLBACK_SEARCH_MS,
            "tokens": 0,
            "result_lines": ["no captured search result"],
        },
        {
            "kind": "model",
            "duration_ms": FALLBACK_MODEL_MS,
            "tokens": 0,
            "result_lines": ["no validated model reply captured"],
        },
    ]


def _step_payload(run_id: str, index: int, step_no: int, step: dict, capture: bool,
                  detail: list[str] | None = None) -> dict:
    """The `aml_step` a client animates: emitted when the step STARTS, with the
    planned duration it should fill the progress bar with."""
    kind = step["kind"]
    if kind == "context":
        label = CONTEXT_LABEL
    elif kind == "tool":
        label = step.get("tool", "tool")
    else:
        label = MODEL_LABEL if capture else FALLBACK_MODEL_LABEL
    payload = {
        "run_id": run_id,
        "index": index,
        "step": step_no,
        "kind": kind,
        "label": label,
        "planned_ms": step["duration_ms"],
        "capture": capture,
    }
    if step.get("tool"):
        payload["tool"] = step["tool"]
    if step.get("args"):
        payload["args"] = step["args"]
    if detail is not None:
        payload["detail"] = detail
    return payload


def _work_alert(run_id: str, index: int, total: int, alert: dict, totals: dict) -> dict:
    """Replay one alert: evidence pack, the captured (or fallback) steps, the
    decision, the ledger row — emitting the front-end contract's events in order.
    Returns the ledger row it recorded."""
    run = CAPTURED.get((alert["customer_id"], alert["typology"]))
    capture = run is not None
    _emit("aml_alert_started", {"run_id": run_id, "index": index, "total": total,
                                "alert": _alert_payload(alert)})

    # Step 0 — the evidence pack, assembled live from FINANCE. It has no capture,
    # but it is the model's entire view of the customer, so the UI gets the lines.
    pack_lines = evidence_pack(alert).split("\n")
    context = {"kind": "context", "duration_ms": CONTEXT_MS}
    _emit("aml_step", _step_payload(run_id, index, 0, context, capture, detail=pack_lines))
    _sleep_ms(CONTEXT_MS)
    _emit("aml_step_finished", {"run_id": run_id, "index": index, "step": 0,
                                "duration_ms": CONTEXT_MS,
                                "result_lines": [f"{len(pack_lines)} lines"]})

    steps = _captured_steps(run) if capture else _fallback_steps(alert)
    tokens = 0
    for step_no, step in enumerate(steps, 1):
        _emit("aml_step", _step_payload(run_id, index, step_no, step, capture))
        _sleep_ms(step["duration_ms"])
        _emit("aml_step_finished", {"run_id": run_id, "index": index, "step": step_no,
                                    "duration_ms": step["duration_ms"],
                                    "tokens": step["tokens"],
                                    "result_lines": step["result_lines"]})
        tokens += step["tokens"]
        # A step that carries metered tokens IS a metered model round-trip: the
        # captured sweep's pre-tool call bills onto the tool step, its answer
        # call onto the model step. Run 4's zeros therefore add nothing, which
        # is exactly how the capture's "6 model calls" is counted.
        if step["tokens"]:
            totals["model_calls"] += 1
        totals["tokens"] += step["tokens"]

    decision = run["decision"] if capture else FALLBACK_DECISION
    # Captured alerts report the run's own elapsed; fallback alerts have no
    # capture, so they report the nominal shape of the steps they just replayed.
    elapsed_ms = run["elapsed_ms"] if capture else CONTEXT_MS + FALLBACK_SEARCH_MS + FALLBACK_MODEL_MS
    mode = "captured" if capture else "fallback"

    _emit("aml_alert_decided", {
        "run_id": run_id, "index": index,
        "decision": {
            "decision": decision["decision"],
            "confidence": decision["confidence"],
            "rationale": decision["rationale"],
            "recommended_next_action": decision["recommended_next_action"],
            "sar_reason_code": decision.get("sar_reason_code") or alert["typology"],
        },
        "mode": mode,
        "elapsed_ms": elapsed_ms,
        "tokens": tokens,
    })

    replayed_at = datetime.now(timezone.utc)
    ledger = {
        "customer_id": alert["customer_id"],
        "customer_name": alert["customer_name"],
        "typology": alert["typology"],
        "risk_rating": alert["risk_rating"],
        "flagged_txns": alert["flagged_txns"],
        "exposure_cents": alert["exposure_cents"],
        "decision": decision["decision"],
        "confidence": decision["confidence"],
        "rationale": decision["rationale"],
        "next_action": decision["recommended_next_action"],
        "sar_reason": decision.get("sar_reason_code") or alert["typology"],
        "mode": mode,
        "elapsed_ms": elapsed_ms,
        "tokens": tokens,
        "replayed_at": replayed_at.isoformat(),
    }
    # The column is a plain TIMESTAMP; bind UTC without the offset.
    _insert_ledger(run_id, ledger, replayed_at.replace(tzinfo=None))
    _emit("aml_alert_recorded", {"run_id": run_id, "index": index, "ledger": ledger})

    totals["captured" if capture else "fallback"] += 1
    return ledger


def _sweep(limit: int) -> None:
    """Work the queue on a background task, then publish the totals."""
    run_id = f"aml-{uuid.uuid4().hex[:10]}"
    started = time.monotonic()
    recorded: list[dict] = []
    totals = {
        "alerts": 0,
        "captured": 0,
        "fallback": 0,
        "model_calls": 0,
        "tokens": 0,
        "seconds": 0.0,
        "captured_seconds": aml_capture.TOTALS["seconds"],
    }
    try:
        alerts = _alert_queue(limit)
        totals["alerts"] = len(alerts)
        _emit("aml_sweep_started", {
            "run_id": run_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "limit": limit,
            "model": aml_capture.MODEL,
            "captured_at": aml_capture.CAPTURED_AT,
            "alerts": [_alert_payload(a) for a in alerts],
        })
        for index, alert in enumerate(alerts, 1):
            try:
                recorded.append(_work_alert(run_id, index, len(alerts), alert, totals))
            except Exception as e:  # one bad alert must not end the desk's morning
                print(f"[aml_replay] alert {index} failed: {type(e).__name__}: {e}")
                _reset_conn()
    except Exception as e:
        print(f"[aml_replay] sweep failed: {type(e).__name__}: {e}")
        _reset_conn()
    finally:
        totals["seconds"] = round(time.monotonic() - started, 1)
        _state["last"] = {
            "run_id": run_id,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "totals": totals,
            "alerts": recorded,
        }
        _state["running"] = False
        _emit("aml_sweep_finished", {"run_id": run_id, "totals": totals, "alerts": recorded})


def _recall() -> None:
    """Replay §6.4: the desk asks its own memory what it decided."""
    capture = aml_capture.RECALL
    run_id = f"recall-{uuid.uuid4().hex[:8]}"
    _state["recalling"] = True
    try:
        _emit("aml_recall_started", {"run_id": run_id, "seconds": capture["seconds"],
                                     "tokens": capture["tokens"]})
        for step in capture["steps"]:
            _sleep_ms(step["duration_ms"])
    finally:
        _state["recalling"] = False
    _emit("aml_recall_finished", {"run_id": run_id, "answer_lines": capture["answer_lines"],
                                  "seconds": capture["seconds"], "tokens": capture["tokens"]})


# --------------------------------------------------------------------------- #
# Public surface
# --------------------------------------------------------------------------- #

def status_payload() -> dict:
    return {
        "state": "running" if _state["running"] else "idle",
        "speed": SPEED,
        "model": aml_capture.MODEL,
        "captured_at": aml_capture.CAPTURED_AT,
        "last": _state["last"],
    }


def sweep_plan(limit: int = DEFAULT_LIMIT) -> dict:
    """One sweep's worth of work, straight from the database: the queue the desk
    would work (with its capture flags) and the evidence pack for its first
    alert. Read-only, no sockets — the acceptance probe and the tests use it."""
    alerts = _alert_queue(limit)
    pack_lines = evidence_pack(alerts[0]).split("\n") if alerts else []
    return {
        "model": aml_capture.MODEL,
        "captured_at": aml_capture.CAPTURED_AT,
        "source": aml_capture.SOURCE,
        "speed": SPEED,
        "limit": limit,
        "queue": [_queue_payload(a) for a in alerts],
        "captured": sum(1 for a in alerts if a["capture"]),
        "fallback": sum(1 for a in alerts if not a["capture"]),
        "evidence_pack_lines": pack_lines,
    }


def init_aml_replay(*, socketio, agent_conn) -> None:
    """Register the replay handlers and create the ledger table."""
    _state["socketio"] = socketio
    _state["conn"] = agent_conn
    ensure_ledger(agent_conn)

    @socketio.on("aml_status_request")
    def _on_status_request(_data=None):
        # `_data` is ignored: socketio passes whatever the client sent, and a
        # client that sends an empty payload must not blow up the handler.
        socketio.emit("aml_status", status_payload(), room=flask_request.sid)
        try:
            alerts = _alert_queue()
        except Exception as e:
            print(f"[aml_replay] queue read failed: {type(e).__name__}: {e}")
            _reset_conn()
            socketio.emit("error", {"message": f"AML queue read failed: {e}"},
                          room=flask_request.sid)
            return
        socketio.emit("aml_queue", {"alerts": [_queue_payload(a) for a in alerts]},
                      room=flask_request.sid)

    @socketio.on("aml_sweep_run")
    def _on_sweep_run(data):
        limit = _clamp_limit((data or {}).get("limit"))
        with _LOCK:
            claimed = not _state["running"]
            if claimed:
                _state["running"] = True
        if not claimed:
            socketio.emit("error", {"message": "An AML sweep is already running."},
                          room=flask_request.sid)
            return
        socketio.emit("aml_status", status_payload())
        try:
            socketio.start_background_task(_sweep, limit)
        except Exception:
            # Never leave `running` set: that would block every later sweep.
            _state["running"] = False
            raise

    @socketio.on("aml_clear")
    def _on_clear(_data=None):
        _state["last"] = None
        socketio.emit("aml_status", status_payload())

    @socketio.on("aml_recall_run")
    def _on_recall_run(_data=None):
        # Claim it here, not inside the task: two quick clicks would otherwise
        # both pass this check before either task ran and replay twice.
        with _LOCK:
            if _state["recalling"]:
                return
            _state["recalling"] = True
        try:
            socketio.start_background_task(_recall)
        except Exception:
            _state["recalling"] = False
            raise

    print(f"  AML replay: {len(aml_capture.RUNS)} captured run(s) · speed x{SPEED:g} · "
          f"ledger {LEDGER_TABLE.lower()} ready")
