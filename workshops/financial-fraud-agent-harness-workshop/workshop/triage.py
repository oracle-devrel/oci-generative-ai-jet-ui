"""Part 6 plumbing: the AML ledger, alert queue, evidence pack, decision validator, meter and reports."""
import json
import re
import time

from workshop.memory import Fact

AML_LEDGER = "AGENT.AML_TRIAGE"
DECISIONS = ("ESCALATE", "KYC_REVIEW", "DISMISS")

TYPOGRAPHY = {
    "STRUCTURING":       "$10,000 CTR threshold - deposits split just under it, repeated in a short window.",
    "GEO_VELOCITY":      "Impossible travel - one card, far-apart regions, hours apart (card cloning / takeover).",
    "HIGH_RISK_COUNTRY": "Wires to elevated-risk corridors (crypto, gold & forex, casinos, remittance) after an inbound credit.",
    "RAPID_CASH_OUT":    "Large inbound wire, then rapid ATM withdrawals draining the account within ~48 hours.",
    "LARGE_CASH_DEPOSIT": "A single cash deposit above $50,000 with no plausible source of funds.",
}


TRIAGE_SYSTEM_PROMPT = """You are the Meridian Bank AML triage analyst operating inside an agent harness.
You receive ONE alert. Decide what the bank should do with it.

Decide exactly one:
  ESCALATE:   the evidence meets the filing bar. Recommend a SAR (new, or an update to an open one).
  KYC_REVIEW: a real signal without enough to file. Request source of funds or refresh KYC.
  DISMISS:    the activity is explained by legitimate behaviour. Write down why an examiner would agree.

Rules:
- Consult your memory first: call search_knowledge for this customer's prior case decisions and the schema
  notes before you decide, and call run_sql if the evidence leaves a question the SQL can answer.
- Judge only the evidence provided; never invent customers, accounts, or amounts.
- Quantify: cite transaction ids and USD amounts (amounts in the alert are already in dollars).
- Weigh repetition, blocked attempts, proximity to reporting thresholds ($10,000 CTR / $50,000),
  prior SARs, and risk_rating.
- If the evidence is thin, say so and choose KYC_REVIEW.

Reply with ONE JSON object and nothing else:
{"decision":"ESCALATE|KYC_REVIEW|DISMISS","confidence":0.0-1.0,"rationale":"<=60 words, cite txn ids and $ amounts",
 "indicators":["..."],"recommended_next_action":"one sentence",
 "sar_reason_code":"STRUCTURING|GEO_VELOCITY|HIGH_RISK_COUNTRY|RAPID_CASH_OUT|LARGE_CASH_DEPOSIT|null"}"""


def rows(conn, sql, **binds):
    """Run SQL and return a list of dicts with lowercase column names."""
    with conn.cursor() as cur:
        cur.execute(sql, **binds)
        cols = [d[0].lower() for d in cur.description]
        return [dict(zip(cols, row)) for row in cur]


def money(cents):
    return f"${(cents or 0) / 100:,.2f}"


# ---------------------------------------------------------------- ledger

def ensure_ledger(conn):
    """Create AGENT.AML_TRIAGE if missing and report how many decisions it holds."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM user_tables WHERE table_name = 'AML_TRIAGE'")
        if not cur.fetchone()[0]:
            cur.execute("""
                CREATE TABLE aml_triage (
                  customer_id    NUMBER(10),
                  typology       VARCHAR2(60),
                  customer_name  VARCHAR2(120),
                  risk_rating    NUMBER(3),
                  flagged_txns   NUMBER(6),
                  exposure_cents NUMBER(15),
                  window_start   TIMESTAMP,
                  window_end     TIMESTAMP,
                  decision       VARCHAR2(20),
                  confidence     NUMBER(3,2),
                  rationale      VARCHAR2(1000),
                  next_action    VARCHAR2(400),
                  sar_reason     VARCHAR2(60),
                  decided_at     TIMESTAMP,
                  decided_by     VARCHAR2(60),
                  CONSTRAINT aml_triage_pk PRIMARY KEY (customer_id, typology)
                )""")
            print(f"created {AML_LEDGER}")
        else:
            print(f"{AML_LEDGER} already present")
    conn.commit()
    n = rows(conn, "SELECT COUNT(*) AS n FROM aml_triage")[0]["n"]
    print(f"ledger: {n} decision(s) on record")
    print("decision vocabulary: ESCALATE · KYC_REVIEW · DISMISS · REVIEW_REQUIRED "
          "(set by the harness, never by the model)")


def record_decision(conn, alert, decision, actor="aml-triage-harness"):
    """MERGE one validated decision into AGENT.AML_TRIAGE, keyed by (customer, typology)."""
    with conn.cursor() as cur:
        cur.execute("""
            MERGE INTO aml_triage t
            USING (SELECT :cid AS customer_id, :typo AS typology FROM dual) s
               ON (t.customer_id = s.customer_id AND t.typology = s.typology)
            WHEN MATCHED THEN UPDATE SET
                 customer_name = :name, risk_rating = :risk, flagged_txns = :n,
                 exposure_cents = :exp, window_start = :ws, window_end = :we,
                 decision = :dec, confidence = :conf, rationale = :rat,
                 next_action = :nxt, sar_reason = :sar,
                 decided_at = SYSTIMESTAMP, decided_by = :actor
            WHEN NOT MATCHED THEN INSERT
                 (customer_id, typology, customer_name, risk_rating, flagged_txns, exposure_cents,
                  window_start, window_end, decision, confidence, rationale, next_action, sar_reason,
                  decided_at, decided_by)
                 VALUES (:cid, :typo, :name, :risk, :n, :exp, :ws, :we, :dec, :conf, :rat, :nxt, :sar,
                         SYSTIMESTAMP, :actor)""",
            cid=alert["customer_id"], typo=alert["typology"], name=alert["full_name"],
            risk=alert["risk_rating"], n=alert["flagged_txns"], exp=alert["exposure_cents"],
            ws=alert["window_start"], we=alert["window_end"], dec=decision["decision"],
            conf=decision["confidence"], rat=decision["rationale"],
            nxt=decision["recommended_next_action"], sar=decision["sar_reason_code"], actor=actor)
    conn.commit()


def case_decision_fact(alert, decision):
    """The memory the agent reads on its next run: one sentence per (customer, typology) decision."""
    body = (f"AML triage {decision['decision']} for customer {alert['customer_id']} "
            f"({alert['full_name']}, risk {alert['risk_rating']}/100), typology {alert['typology']}, "
            f"exposure {money(alert['exposure_cents'])}: {decision['rationale']} "
            f"Next action: {decision['recommended_next_action']}")
    return Fact(kind="case_decision", subject=f"case:{alert['customer_id']}:{alert['typology']}", body=body,
                metadata={"source": "aml_triage", "decision": decision["decision"],
                          "typology": alert["typology"], "customer_id": int(alert["customer_id"]),
                          "confidence": decision["confidence"]})


def print_ledger(conn):
    print("Ledger: AGENT.AML_TRIAGE (what a reviewer or examiner would query)")
    for r in rows(conn, """
            SELECT customer_id, customer_name, typology, decision, confidence,
                   exposure_cents, next_action
              FROM aml_triage ORDER BY decided_at DESC"""):
        print(f"  cust {r['customer_id']:>3}  {r['customer_name']:<18} {r['typology']:<18} "
              f"{r['decision']:<16} conf {r['confidence']:.2f}  {money(r['exposure_cents']):>14}  "
              f"{(r['next_action'] or '')[:60]}")


# ---------------------------------------------------------------- queue

_ALERT_QUEUE_SQL = """
WITH flagged AS (
  SELECT a.customer_id, t.flag_reason, t.txn_id, t.txn_ts, t.amount_cents, t.channel, t.status
    FROM FINANCE.transactions t
    JOIN FINANCE.accounts a ON a.account_id = t.account_id
   WHERE t.status IN ('FLAGGED','BLOCKED') AND t.flag_reason IS NOT NULL
     AND t.txn_ts >= SYSTIMESTAMP - NUMTODSINTERVAL(:days, 'DAY')
)
SELECT f.customer_id, cu.full_name, cu.segment, cu.country, cu.risk_rating,
       f.flag_reason AS typology,
       COUNT(*) AS flagged_txns,
       SUM(f.amount_cents) AS exposure_cents,
       MIN(f.txn_ts) AS window_start, MAX(f.txn_ts) AS window_end,
       COUNT(DISTINCT f.channel) AS channels,
       SUM(CASE WHEN f.status = 'BLOCKED' THEN 1 ELSE 0 END) AS blocked_txns,
       (SELECT COUNT(*) FROM FINANCE.sar_reports s WHERE s.customer_id = f.customer_id) AS prior_sars
  FROM flagged f
  JOIN FINANCE.customers cu ON cu.customer_id = f.customer_id
 GROUP BY f.customer_id, cu.full_name, cu.segment, cu.country, cu.risk_rating, f.flag_reason
 ORDER BY cu.risk_rating DESC, SUM(f.amount_cents) DESC
"""


def alert_queue(conn, lookback_days=30, ignore_watermark=True):
    """The alerts to work, one row per (customer, AML typology), riskiest first."""
    alerts = rows(conn, _ALERT_QUEUE_SQL, days=lookback_days)
    if not ignore_watermark:
        with conn.cursor() as cur:
            cur.execute("SELECT MAX(window_end) FROM aml_triage")
            watermark = cur.fetchone()[0]
        if watermark:
            print(f"watermark: only alerts newer than {watermark:%Y-%m-%d %H:%M}")
            alerts = [a for a in alerts if a["window_end"] > watermark]
    return alerts


def print_queue(alerts, limit, lookback_days):
    total = sum(a["exposure_cents"] for a in alerts)
    scope = f"showing the top {limit}" if len(alerts) > limit else "all"
    print(f"{len(alerts)} alert(s) in the {lookback_days}-day window, "
          f"{money(total)} of flagged activity, {scope}")
    for a in alerts[:limit]:
        print(f"  [risk {a['risk_rating']:>3}] {a['full_name']:<18} {a['typology']:<18} "
              f"txns={a['flagged_txns']:>2}  exposure={money(a['exposure_cents']):>14}  "
              f"blocked={a['blocked_txns']}  prior SARs={a['prior_sars']}")


# ---------------------------------------------------------------- evidence

def _txn_line(t, region=False):
    line = (f"  txn {t['txn_id']:>5}  {t['seen_at']}  {money(t['amount_cents']):>13}  "
            f"{t['channel']}/{t['txn_type']}  status={t['status']}  ")
    if region:
        line += f"region={t['region']}  "
    return line + f"merchant={t['merchant'] or '-'}"


def evidence_pack(conn, alert, max_txns=8):
    """Everything the agent may see about one alert, as text built from SQL.

    All of it is scoped to the alert's own window, so the header totals match the rows."""
    cid, typology, wstart = alert["customer_id"], alert["typology"], alert["window_start"]
    lines = [f"ALERT  customer {cid} | {alert['full_name']} | {alert['segment']} | "
             f"{alert['country']} | risk_rating {alert['risk_rating']}/100",
             f"RULE   {typology}: {TYPOGRAPHY.get(typology, '')}",
             f"QUEUE  {alert['flagged_txns']} flagged txn(s), {money(alert['exposure_cents'])} total, "
             f"{alert['window_start']:%Y-%m-%d} to {alert['window_end']:%Y-%m-%d}, "
             f"{alert['channels']} channel(s), {alert['blocked_txns']} blocked attempt(s)",
             "FLAGGED TRANSACTIONS IN THIS WINDOW (newest first; amounts in USD):"]
    lines += [_txn_line(t, region=True) for t in rows(conn, """
            SELECT t.txn_id, TO_CHAR(t.txn_ts,'YYYY-MM-DD HH24:MI') AS seen_at, t.amount_cents,
                   t.channel, t.txn_type, t.status, t.region, m.name AS merchant
              FROM FINANCE.transactions t
              JOIN FINANCE.accounts a ON a.account_id = t.account_id
              LEFT JOIN FINANCE.merchants m ON m.merchant_id = t.merchant_id
             WHERE a.customer_id = :cid AND t.status IN ('FLAGGED','BLOCKED')
               AND t.flag_reason = :typo AND t.txn_ts >= :wstart
             ORDER BY t.txn_ts DESC FETCH FIRST :n ROWS ONLY""",
            cid=cid, typo=typology, wstart=wstart, n=max_txns)]

    h = rows(conn, """
            SELECT COUNT(*) AS older_txns,
                   TO_CHAR(MIN(t.txn_ts),'YYYY-MM-DD') AS first_seen,
                   TO_CHAR(MAX(t.txn_ts),'YYYY-MM-DD') AS last_seen
              FROM FINANCE.transactions t
              JOIN FINANCE.accounts a ON a.account_id = t.account_id
             WHERE a.customer_id = :cid AND t.status IN ('FLAGGED','BLOCKED')
               AND (t.flag_reason <> :typo OR t.flag_reason IS NULL OR t.txn_ts < :wstart)""",
             cid=cid, typo=typology, wstart=wstart)[0]
    if h["older_txns"]:
        lines.append(f"FLAGGED HISTORY (outside this window): {h['older_txns']} earlier flagged "
                     f"txn(s), {h['first_seen']} to {h['last_seen']}. Context only: this decision "
                     f"covers the window above.")

    lines.append("RECENT ACTIVITY, ANY STATUS (top 6 by amount, last 30 days, includes unflagged "
                 "transactions):")
    lines += [_txn_line(t) for t in rows(conn, """
            SELECT t.txn_id, TO_CHAR(t.txn_ts,'YYYY-MM-DD HH24:MI') AS seen_at, t.amount_cents,
                   t.channel, t.txn_type, t.status, m.name AS merchant
              FROM FINANCE.transactions t
              JOIN FINANCE.accounts a ON a.account_id = t.account_id
              LEFT JOIN FINANCE.merchants m ON m.merchant_id = t.merchant_id
             WHERE a.customer_id = :cid AND t.txn_ts >= SYSTIMESTAMP - INTERVAL '30' DAY
             ORDER BY t.amount_cents DESC FETCH FIRST 6 ROWS ONLY""", cid=cid)]

    for a in rows(conn, """
            SELECT a.account_id, a.account_type, a.currency, a.balance_cents, b.city, b.region
              FROM FINANCE.accounts a JOIN FINANCE.branches b ON b.branch_id = a.branch_id
             WHERE a.customer_id = :cid ORDER BY a.opened_ts""", cid=cid):
        lines.append(f"ACCOUNT #{a['account_id']} {a['account_type']} {a['currency']} "
                     f"balance {money(a['balance_cents'])} ({a['city']}, {a['region']})")

    flow = rows(conn, """
            SELECT SUM(CASE WHEN t.txn_type IN ('DEPOSIT','WIRE_IN') THEN t.amount_cents ELSE 0 END) AS money_in,
                   SUM(CASE WHEN t.txn_type IN ('WITHDRAWAL','WIRE_OUT') THEN t.amount_cents ELSE 0 END) AS money_out
              FROM FINANCE.transactions t JOIN FINANCE.accounts a ON a.account_id = t.account_id
             WHERE a.customer_id = :cid AND t.txn_ts >= SYSTIMESTAMP - INTERVAL '30' DAY""",
                cid=cid)[0]
    lines.append(f"30-DAY FLOW: money-in {money(flow['money_in'])} | money-out {money(flow['money_out'])}")

    for s in rows(conn, """
            SELECT sar_id, reason_code, status, TO_CHAR(filed_ts,'YYYY-MM-DD') AS filed,
                   SUBSTR(narrative, 1, 180) AS narrative
              FROM FINANCE.sar_reports WHERE customer_id = :cid ORDER BY filed_ts DESC""", cid=cid):
        lines.append(f"PRIOR SAR {s['sar_id']}: {s['reason_code']} status={s['status']} "
                     f"filed {s['filed']}: {s['narrative']}")
    return "\n".join(lines)


def show_pack(pack):
    print(pack)
    print(f"\n[{len(pack.splitlines())} lines, {len(pack)} chars: the model's entire view of this customer]")


# ---------------------------------------------------------------- validator

def extract_json(text):
    """Find the JSON object in a model reply, even when it is wrapped in prose."""
    match = re.search(r"\{.*\}", text or "", re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        try:
            return json.loads(re.sub(r"\s+", " ", match.group(0)))
        except json.JSONDecodeError:
            return None


def validate_decision(payload, alert):
    """Clamp whatever the model said to something the bank allows. Never raises."""
    if not isinstance(payload, dict):
        return {"decision": "REVIEW_REQUIRED", "confidence": 0.0,
                "rationale": "Model reply was not valid JSON; a human must work this alert.",
                "indicators": [], "recommended_next_action": "Human review of the raw reply.",
                "sar_reason_code": alert["typology"]}
    decision = str(payload.get("decision", "")).strip().upper()
    if decision not in DECISIONS:
        decision = "REVIEW_REQUIRED"
    try:
        confidence = max(0.0, min(1.0, float(payload.get("confidence", 0.0))))
    except (TypeError, ValueError):
        confidence = 0.0
    reason = str(payload.get("sar_reason_code") or "").strip().upper()
    if reason not in TYPOGRAPHY:
        reason = alert["typology"]
    return {
        "decision": decision,
        "confidence": confidence,
        "rationale": str(payload.get("rationale") or "")[:900],
        "indicators": [str(i)[:60] for i in (payload.get("indicators") or [])][:6],
        "recommended_next_action": str(payload.get("recommended_next_action") or "")[:380],
        "sar_reason_code": reason,
    }


def check_validator():
    for probe, expected in [({"decision": "escalate", "confidence": 1.7, "sar_reason_code": "made_up"}, "ESCALATE"),
                            ("not json at all", "REVIEW_REQUIRED")]:
        got = validate_decision(probe, {"typology": "STRUCTURING"})["decision"]
        assert got == expected, f"validator drift: {got} != {expected}"
    print("✅ decision validator holds: unknown decisions become REVIEW_REQUIRED, confidence is clamped, "
          "reason codes are restricted to the bank's typologies")


# ---------------------------------------------------------------- meter

USAGE = {"calls": 0, "tokens": 0, "seconds": 0.0}


def meter(chat_fn):
    """Wrap a chat function so every model call is counted in USAGE. Safe to apply twice."""
    if getattr(chat_fn, "_metered", False):
        return chat_fn

    def metered(*args, **kwargs):
        started = time.time()
        response = chat_fn(*args, **kwargs)
        USAGE["calls"] += 1
        USAGE["seconds"] += time.time() - started
        USAGE["tokens"] += getattr(getattr(response, "usage", None), "total_tokens", 0) or 0
        return response

    metered._metered = True
    return metered


# ---------------------------------------------------------------- reports

def print_decision(i, n, alert, record):
    print(f"\n[{i}/{n}] customer {alert['customer_id']} · {alert['typology']} · "
          f"{money(alert['exposure_cents'])} flagged exposure")
    print(f"   -> {record['decision']:<16} confidence {record['confidence']:.2f}")
    print(f"      {record['rationale']}")
    print(f"      next: {record['recommended_next_action']}")


def print_run_summary(n_records, n_failed, started):
    print(f"\n{n_records} decision(s) in {time.time() - started:.0f}s · "
          f"{USAGE['calls']} model call(s) · {USAGE['tokens']:,} tokens")
    if n_failed and not n_records:
        print("\nEvery alert failed. If the traceback says a TODO is still a stub, finish the TODOs "
              "above before running Part 6.")


def run_queue(queue, triage_alert, thread_id):
    """Triage each alert in turn. One failing alert is reported and skipped, never stops the run."""
    if not queue:
        print("Queue empty. Set IGNORE_WATERMARK = True above to re-triage the same window.")
        return []
    records, failed, started = [], 0, time.time()
    for i, alert in enumerate(queue, 1):
        try:
            record = triage_alert(alert, thread_id=thread_id)
        except Exception as exc:
            failed += 1
            print(f"   ! alert {i} failed: {type(exc).__name__}: {str(exc)[:200]}")
            continue
        records.append(record)
        print_decision(i, len(queue), alert, record)
    print_run_summary(len(records), failed, started)
    return records


def impact_board(conn, manual_minutes_per_alert):
    """Print the morning briefing, computed from the ledger and FINANCE."""
    by_decision = rows(conn, """
            SELECT decision, COUNT(*) AS alerts, SUM(exposure_cents) AS exposure_cents
              FROM aml_triage GROUP BY decision ORDER BY alerts DESC, exposure_cents DESC""")
    total = sum(r["alerts"] for r in by_decision)
    by = {r["decision"]: r for r in by_decision}
    escalated = by.get("ESCALATE", {"alerts": 0, "exposure_cents": 0})
    review = by.get("REVIEW_REQUIRED", {"alerts": 0, "exposure_cents": 0})
    conf = rows(conn, "SELECT ROUND(AVG(confidence), 2) AS avg_conf FROM aml_triage "
                      "WHERE decision <> 'REVIEW_REQUIRED'")[0]["avg_conf"]
    sars = rows(conn, "SELECT COUNT(*) AS total, SUM(CASE WHEN status = 'FILED' THEN 1 ELSE 0 END) AS filed "
                      "FROM finance.sar_reports")[0]
    ages = rows(conn, "SELECT ROUND(MAX(CAST(SYSTIMESTAMP AS DATE) - CAST(window_end AS DATE))) AS oldest, "
                      "       ROUND(AVG(CAST(SYSTIMESTAMP AS DATE) - CAST(window_end AS DATE))) AS average "
                      "  FROM aml_triage")[0]
    age = (f"{int(ages['oldest'])}d  (avg {int(ages['average'])}d)"
           if ages["oldest"] is not None else "n/a: the ledger is empty, run the queue first")
    manual_hours = total * manual_minutes_per_alert / 60.0

    print("MERIDIAN BANK · AML ALERT TRIAGE · MORNING BRIEFING")
    print("=" * 72)
    print(f"  alerts decided by the harness .......... {total}")
    for r in by_decision:
        bar = "█" * max(1, int(32 * r["alerts"] / max(total, 1)))
        print(f"    {r['decision']:<16} {r['alerts']:>3}  {bar}  {money(r['exposure_cents'])}")
    print(f"  flagged exposure escalated to compliance {money(escalated['exposure_cents'])}")
    print(f"  average confidence on decided alerts ... {conf if conf is not None else 'n/a'}")
    print(f"  oldest alert worked (now - newest txn) . {age}")
    print("-" * 72)
    print(f"  harness cost ........................... {USAGE['calls']} model call(s) · "
          f"{USAGE['tokens']:,} tokens · {USAGE['seconds']:.0f}s of model wall-clock")
    print(f"  equivalent manual effort ............... {manual_hours:.1f}h at "
          f"{manual_minutes_per_alert:.0f} min/alert (assumption)")
    print(f"  SAR history on file .................... {sars['total']} report(s), {sars['filed']} filed")
    if review["alerts"]:
        print(f"  human review required .................. {review['alerts']} alert(s), "
              f"the model's reply did not validate")
    print("=" * 72)
    print("What the harness did NOT do: file anything, write to FINANCE, or see data its persona "
          "is not entitled to.")
    print("The recommendation is a decision record; a human signs the filing.")
