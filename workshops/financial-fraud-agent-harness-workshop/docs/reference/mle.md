# Oracle MLE Compute Sandbox


> 🧭 **Advanced reference.** Oracle MLE compute is not part of the notebook. It is live in the running app (`exec_js`); the notebook does not use it.
LLMs are unreliable at math. Percentiles, weighted means, post-fetch reshaping — anything quantitative — should run in a deterministic engine, not in the model's head. We route those snippets through Oracle's **Multilingual Engine (MLE)** — JavaScript that runs *inside* the Oracle process, called via [`DBMS_MLE`](https://docs.oracle.com/en/database/oracle/oracle-database/26/dbmle/index.html).

## Why JavaScript and not Python?

Oracle AI Database 26ai Free ships MLE with JavaScript. Python MLE is a separate package not enabled in this build, which surfaces as `ORA-04101: Multilingual Engine does not support the language PYTHON`. The agent doesn't care which language we expose — it'll happily emit JS for the kinds of computation we need (arithmetic, string formatting, JSON reshaping).

## Why MLE rather than a subprocess sandbox?

- **MLE is a *language* sandbox, not a *privilege* sandbox — except that `exec_js` removes the privilege.** GraalVM blocks filesystem, network, native code and the OS shell, and a bare MLE context would also hand the script `session` / `oracledb` (a live `AGENT` connection that can read tables `run_sql` refuses). The `exec_js` wrapper (`app/backend/agent/mle.py`) captures `mle-js-bindings` for itself, then deletes those globals and replaces `require` with one that always throws `module <name> is not available in exec_js`, so model-written JS gets no database access. Code run directly via `DBMS_MLE.EVAL` outside `exec_js` still inherits `AGENT`'s grants via `mle-js-oracledb` — narrow them if that matters.
- **No exfiltration channel by construction.** The polyglot engine doesn't expose filesystem, network, or native libs, so agent-authored code can't open sockets or read `~/.ssh/`.
- **Code runs next to the data.** Snippets that operate over rows the agent just retrieved don't round-trip those rows back out to a separate process.
- **Zero local install.** GraalVM ships *inside* the database. No Python, Java, or GraalVM on the laptop running the harness.

## What's pre-built

Nothing in Oracle itself — MLE is available out of the box on Oracle AI Database 26ai with the grants `app/scripts/bootstrap.py` already gave to `AGENT`:

- `EXECUTE ON DBMS_MLE`
- `EXECUTE DYNAMIC MLE`
- `DB_DEVELOPER_ROLE`

This Part just defines the Python helper that calls `DBMS_MLE.EVAL` for us.

## The `exec_js` helper

`exec_js(code)` wraps your JS in a `try/catch` + `console.log` capture, evaluates it inside a fresh MLE context, and returns:

```python
{"stdout": "<captured console.log>", "stderr": "<error if thrown>", "ok": True/False}
```

The wrapper takes `require("mle-js-bindings")` before the model's code runs and uses it to export a `result` value, which the Python side imports via `DBMS_MLE.IMPORT_FROM_MLE` and parses as JSON. Inside the model's code `require` is blocked.

## Why the agent will actually reach for it

The app's system prompt has an explicit rule:

> *"For numeric work over fetched rows ... you MUST fetch with `run_sql` and then call `exec_js` to compute."*

This pushes percentile / mean / max / unit-conversion / reshaping work through MLE rather than letting the model do arithmetic in its head or rely solely on SQL aggregation. Without that rule GPT-class models often skip the JS hop and answer from a single `run_sql` aggregate — convenient but harder to audit when the math gets non-trivial.

## A concrete example

```javascript
const totals = [199, 4999, 12999, 599, 8999, 24999, 1499, 89999, 3499, 599, 19999, 11999]
                 .slice().sort((a, b) => a - b);
const n = totals.length;
function pct(p) {
    const k = (n - 1) * p;
    const f = Math.floor(k);
    return f === Math.min(f + 1, n - 1)
         ? totals[f]
         : totals[f] + (totals[Math.min(f + 1, n - 1)] - totals[f]) * (k - f);
}
const sum = totals.reduce((a, b) => a + b, 0);
console.log("n=" + n + " mean=" + Math.floor(sum/n) +
            " p50=" + Math.round(pct(0.50)) + " p95=" + Math.round(pct(0.95)));
```

The model emits this JS in response to "compute percentiles over these order totals", `exec_js` runs it inside Oracle, and the result lands back in the agent's context as deterministic, audit-traceable output.

## Key takeaways

- **LLMs are unreliable at math.** Percentiles, weighted means, post-fetch reshaping — anything quantitative — should run in a deterministic engine, not in the model's head.
- **MLE is a *language* sandbox, not a *privilege* sandbox.** GraalVM blocks I/O and arbitrary syscalls; `exec_js` additionally strips `session`/`oracledb` so it has no DB access. No subprocess, no network, no extra install.
- **The audit trail is the actual computation.** Routing math through `exec_js` means the trace shows the JS source, the inputs, and the result — not a number the LLM claims is correct.

## Troubleshooting

**`ORA-04101: Multilingual Engine does not support the language PYTHON`** — Use JavaScript. Python MLE isn't enabled on Free.

**No `stdout` but `ok: true`** — The snippet didn't call `console.log`. Wrap your final value in `console.log(...)` to capture it.

**`stderr: "module <name> is not available in exec_js"`** — By design: `exec_js` blocks `require` for model code. Compute over the values you pass in; fetch data with `run_sql`. (Running a snippet directly via `DBMS_MLE.EVAL` outside `exec_js`, you handle bindings yourself.)

**`ORA-04036: PGA memory ... exceeds PGA_AGGREGATE_LIMIT`** — Raise `pga_aggregate_limit`. The provisioning scripts do not change it (the Free default is 2 GiB); as `SYSDBA` against `CDB$ROOT`, set it to 4G — see [troubleshooting](../troubleshooting.md).
