# Part 6: Autonomous AML Triage

**The goal of this part:** stop responding and start deciding. Parts 1–5 built a harness that answers
when asked; this part runs the same harness as an AML desk — it reads incoming alert data from
`FINANCE`, decides what the bank should do (**with a reason and a confidence**), records the decision
where a human can replay it, and reports what the run was worth.

There is no TODO in this part. It runs the harness from the eight TODOs.

Start here: **`notebook_student.ipynb` §6.1–§6.4** (or `notebook_complete.ipynb` for the
solved run). This guide is the reference for what each cell does and why.

---

## The four properties that make it autonomy

A model that answers a question is a query tool. A model that works a queue is a colleague. The
difference is four properties, and each one is something you can point at in the notebook:

| Property | Where it lives |
|---|---|
| **A trigger, not a prompt** — the run starts from queued data | §6.1 builds the alert queue from `FINANCE` |
| **A decision with a stated reason** — not a summary of rows | §6.2 policy + validator → §6.3 `triage_alert` |
| **A durable record a human can replay** | `AGENT.AML_TRIAGE` rows + OAMP `kind="case_decision"` memories |
| **A budget and a boundary** | metered model calls, ≤6 iterations / 120 s per alert, `ESCALATE` *recommends* — it never files |

Take the boundary away and the other three are a liability: an unbounded process that writes to a
regulated ledger without a human signature is exactly what compliance teams exist to prevent.

## What an alert is

The fraud signal lives in `FINANCE` — the same schema the agent scanned in Part 2:

| Where | What it holds | Why it matters |
|---|---|---|
| `transactions.status` | `COMPLETED` / `FLAGGED` / `BLOCKED` | The bank's own rules already fired; this *is* the queue |
| `transactions.flag_reason` | which AML typology fired | Turns a transaction row into an investigation |
| `transactions.amount_cents` | integer USD **cents** | ÷100. The seed plants this trap on purpose |
| `customers.risk_rating` | 1–100, higher is riskier | Weights the queue |
| `sar_reports` | what compliance already filed | Prior history changes today's decision |

The five seeded typologies:

| `flag_reason` | Pattern |
|---|---|
| `STRUCTURING` | Cash deposits just under the $10,000 CTR threshold, repeated in a short window |
| `GEO_VELOCITY` | One card, two far-apart regions, hours apart (one attempt `BLOCKED`) |
| `HIGH_RISK_COUNTRY` | Wires to elevated-risk corridors right after an inbound credit |
| `RAPID_CASH_OUT` | Inbound wire, then ATM withdrawals within ~48 hours |
| `LARGE_CASH_DEPOSIT` | A single cash deposit above $50,000 |

**An alert is not a transaction.** A row says *"this deposit was $9,983"*. An alert says *"this
customer made nine deposits between $8,000 and $9,999 in two weeks, across ATM and branch channels,
and already has a SAR under review."* The notebook groups by `(customer, typology)` in one SQL
statement (§6.1) — deciding on single transactions means deciding on noise.

## The run, cell by cell

### The triage ledger (§6.1, `ensure_ledger`)

Two stores, two audiences, deliberately:

| Store | Shape | Read by |
|---|---|---|
| `AGENT.AML_TRIAGE` | one row per `(customer, typology)`: decision, confidence, rationale, evidence window, who decided | an examiner, a dashboard — structured and replayed with SQL |
| OAMP memory, `kind="case_decision"` | the same decision as a sentence | **the agent**, next run — semantic recall |

Same split as `scan_history` in the app: the harness owns its own state, in its own schema, beside the
memory tables. Nothing is ever written to `FINANCE`.

### The queue (§6.1)

Three knobs:

| Knob | Default | Effect |
|---|---|---|
| `ALERT_LOOKBACK_DAYS` | `30` | How far back "incoming" reaches |
| `TRIAGE_LIMIT` | `3` | Alerts worked per run (raise once the first pass is green) |
| `IGNORE_WATERMARK` | `True` | `False` makes the desk **incremental**: only alerts whose newest flagged transaction is newer than `MAX(window_end)` in the ledger. A second run in the same window then reports *"0 new alerts"* — which is the honest behaviour of a scheduled job |

The seeded bank produces many alerts across the five typologies. They are true positives *by
construction* (the seed plants the patterns), so an ESCALATE-heavy run is expected. A production queue
is the mirror image — 90 %+ explainable — which is exactly why dismissals have to be written down: a
dismissal is only cheap if the reason survives review.

### The evidence pack (§6.2)

Assembled in SQL, and it is the *only* thing the model sees:

1. the alert header (customer, segment, country, risk rating, typology, window, blocked attempts);
2. the flagged transactions **inside the alert's window** (so the numbers the model reasons over match
   the header totals), newest first, with merchant names where the channel has one, plus a one-line
   summary of older flagged history that deliberately stays *outside* this alert's arithmetic;
3. **recent activity of any status** (top 6 by amount, 30 days) — the context a single flagged row
   cannot carry: the inbound wire *before* the cash-out, the inbound credit *before* the wires
   to the high-risk corridor;
4. accounts and balances;
5. money-in / money-out over 30 days;
6. prior SARs with their reason, status, filing date, and narrative.

The model may ask for more inside its budget — and the triage prompt tells it to check memory first
(`search_knowledge`) before deciding, which is how yesterday's case note shows up in today's
decision. But it does not get to choose its evidence. That is the harness's job, and it is what makes
the decision reproducible.

### The policy and the validator (§6.2)

| Decision | Authorises | Driven by |
|---|---|---|
| `ESCALATE` | Recommend a SAR (new, or an update to an open one) | Repetition, blocked attempts, prior SAR, threshold proximity |
| `KYC_REVIEW` | Investigate before filing — source-of-funds, KYC refresh | A real signal on thin evidence |
| `DISMISS` | Close the alert **with a written reason** an examiner would accept | Activity explained by legitimate behaviour |

The model returns JSON. The harness validates it and enforces two rules:

- A decision outside the vocabulary becomes **`REVIEW_REQUIRED`** — a human works it. Never an
  exception, never a silent pass-through, never a guess.
- A `sar_reason_code` outside the bank's five typologies falls back to the alert's own typology.
  **The model owns the reasoning; the harness owns the enum.**

### `triage_alert` (§6.3)

One alert in, one ledger row and one memory out. It calls **`agent_turn`** — the loop from TODO 8 —
unchanged: same context assembly, same tool dispatch, same iteration and wall-clock budgets.
Autonomy is not a different loop; it is the same loop with a trigger and a record.

Three details worth pausing on:

1. The triage instruction travels in the **user message**, not in a rewritten system prompt. The loop
   stays reusable; only the job description changes. Because the thread keeps its memories, alert #3
   is triaged by an agent that remembers what it decided on #1 and #2.
2. Every decision is written **twice on purpose**: structured row for the examiner, memory for the
   agent.
3. `chat` is wrapped with a **meter** from this point on, so §6.4 can report what autonomy cost in
   model calls, tokens, and wall-clock — the numbers an ops review will ask for first.

### The run (§6.3)

`run_triage()` works the queue and prints a line per alert: decision, confidence, rationale, next
action. One alert failing never kills the run — the harness records the failure, prints it, and moves
on. That is not defensive padding; it is the difference between "the desk ran" and "the desk stopped
because one customer's data was odd".

### The impact board (§6.4)

Computed from the ledger, `FINANCE`, and the meter: alerts decided, decisions split, exposure
escalated, average confidence, alert age, model calls/tokens/seconds, and the equivalent manual effort.

Exactly **one** input is an assumption, and it is labelled as one:

```python
MANUAL_MINUTES_PER_ALERT = 45.0   # ASSUMPTION, not a measurement — change it and re-run
```

Everything else came out of the database. The board ends by stating what the harness did **not** do:
file anything, write to `FINANCE`, or see data its persona is not entitled to. The recommendation is a
decision record; a human signs the filing.

### Close the loop (§6.4)

Because decisions are memories, the same `agent_turn` can answer questions about its own morning
("which customers did you escalate, what is under review, what should a human pick up first?"). The
answer is grounded in the rationales it wrote minutes earlier — the difference between a decision log
and a colleague who was there.

## The decision record

```sql
SELECT customer_id, customer_name, typology, decision, confidence,
       ROUND(exposure_cents/100, 2) AS exposure_usd, rationale, next_action, decided_at
  FROM aml_triage
 ORDER BY decided_at DESC;
```

That is the whole audit surface: who, what, why, how sure, how much, and when.

## Knobs and their defaults

| Knob | Where | Default |
|---|---|---|
| `ALERT_LOOKBACK_DAYS` | §6.1 | `30` |
| `TRIAGE_LIMIT` | §6.1 | `3` |
| `IGNORE_WATERMARK` | §6.1 | `True` |
| `max_iterations` / `budget_seconds` per alert | §6.3 inside `triage_alert` | `6` / `120.0` |
| `MANUAL_MINUTES_PER_ALERT` | §6.4 | `45.0` *(assumption)* |

## From one morning to a programme

| Next step | How, in this stack |
|---|---|
| **Run it every morning** | A `DBMS_SCHEDULER` job — the app already does this for schema scans (`app/backend/db/scheduler_setup.py`); the queue, decisions, and ledger are plain SQL |
| **Make it incremental** | `IGNORE_WATERMARK = False` — only alerts newer than the last run |
| **Keep a human in the loop** | `REVIEW_REQUIRED` routes unvalidated output to a person; sample a percentage of `DISMISS` decisions as a standing control |
| **Watch precision, not volume** | `SELECT decision, COUNT(*) FROM aml_triage GROUP BY decision` is the programme's false-positive rate over time |
| **Prove it to an examiner** | Every row carries its evidence window, rationale, and confidence; the same text is retrievable from OAMP |
| **Scope it by identity** | Run the desk as `compliance.officer` vs `analyst.east`: the same queue returns different rows, because the kernel decides — see the [Deep Data Security reference](reference/deep-data-security.md) |

Honest limits: a model that decides can be wrong at scale, the policy is only as good as the
thresholds in it, and the seed's queue is true-positive-weighted by construction. What this part shows
is not that the agent is right — it is that its judgement arrives **with evidence, a reason, a record,
and a budget**, which is the only form of autonomy a regulated business can deploy.

## Troubleshooting

**`ORA-00942: table or view does not exist` on `aml_triage`** — the §6.1 ledger cell has not run. It creates
the table once, in the `AGENT` schema.

**The queue prints `0 alert(s)`** — either the lookback window is too small for the seeded activity, or
`IGNORE_WATERMARK = False` and everything in the window was already triaged. Set
`IGNORE_WATERMARK = True`, or check `SELECT COUNT(*) FROM aml_triage`.

**A row says `REVIEW_REQUIRED`** — the model's reply did not parse as JSON, or its decision was outside
the vocabulary. That is the intended fallback, not a bug: read the `rationale` column, and if it
happens often, lower the temperature of your model or shrink the evidence pack.

**Every alert failed with a stub error** — a TODO is still unimplemented. Part 6 calls
`agent_turn`, `retrieve_tools`, `retrieve_knowledge`, and `tool_run_sql`; finish TODOs 1–8 first, or run
`notebook_complete.ipynb`.

**Triage is slow / hits rate limits** — each alert is a bounded multi-step loop (context build, tool
call, decision). Lower `TRIAGE_LIMIT`, or rely on the OCI key rotation from §1.1
(`OCI_GENAI_API_KEY_2..6`).

**Re-running Part 6 and the impact board is not growing** — expected: the ledger upserts on
`(customer, typology)`. Set `IGNORE_WATERMARK = False` (for the watermark behaviour) or raise
`TRIAGE_LIMIT` to work more of the queue.

## Key takeaways

- **Autonomy = trigger + decision + record + budget.** Remove any one and you have a demo, not a
  process.
- **The model owns the judgement; the harness owns the state.** Validation, enums, persistence, and
  budgets are harness code — nothing the model can talk its way past.
- **Write the decision twice.** A structured row for the examiner, a memory for the next run. Semantic
  recall and auditability are different requirements.
- **Deciding is not the deliverable — deciding *traceably* is.** Evidence windows, rationales, and
  confidences are what let a human sign the filing.
- **Measure it in the same notebook.** Alerts, exposure, model calls, equivalent manual effort: the
  business case and the harness live in the same ledger.
