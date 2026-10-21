# Identity-Aware Data Access — from Python filters to the kernel

> **Oracle documentation:** [`Oracle Deep Data Security Guide, 26ai`](https://docs.oracle.com/en/database/oracle/oracle-database/26/ddscg/index.html)
> · [`Deep Data Security product page`](https://www.oracle.com/security/database-security/features/deep-data-security/)

> 🧭 **Advanced reference.** Not part of the notebook. The rule set is seeded by `app/scripts/setup_deep_security.py` (part of the Codespace's idempotent provisioning), the running app drives it on every read, and this guide is the reference for the design.

The earlier Parts give the agent memory and tools. This guide asks a different question: **what is the agent allowed to see, and who decides?**

The harness has personas — the `Use As:` dropdown in the app, defined in
[`app/backend/api/identities.py`](../../app/backend/api/identities.py). Each carries a clearance,
authorized regions, columns to redact, and tables to refuse. The interesting part is not *which*
rules exist. It is **where they run**.

## The problem: a filter is not a boundary

If the rules live in Python, the database has already handed over the rows by the time they apply.
The agent asks for `SELECT * FROM FINANCE.TRANSACTIONS`, Oracle returns all four regions, and a
`for` loop in Flask throws some away. That is a UI preference with a security-shaped comment above
it, and it holds only until someone finds a path around the loop.

### The bug that proves it

This repository's own persona registry shipped this rule:

```python
_ACCOUNT_IDENTIFIER_MASKS = ["FINANCE.ACCOUNTS.ACCOUNT_NUMBER", ...]
```

`FINANCE.ACCOUNTS` has **no `ACCOUNT_NUMBER` column**. It never did — the account key is the
numeric `ACCOUNT_ID`, and the sensitive value on that table is `BALANCE_CENTS`. In Python the rule
failed silently, because a mask naming a nonexistent column is indistinguishable from a mask that
works. The moment the same rule is pushed into the database, Oracle rejects it:

```
ORA-23607: invalid column "ACCOUNT_NUMBER"
```

That is the whole argument for this part. A rule the kernel cannot compile is a rule you learn about
immediately. A rule the application "applies" is a rule you learn about in the incident review.

## What Oracle Deep Data Security is

Oracle **Deep Data Security** ("Deep Sec") is the database-native authorization model introduced in
**Oracle AI Database 26ai** for exactly this situation: agents and applications querying on behalf of
an end user.

| Concept | Statement | What it does |
|---|---|---|
| **Data grant** | `CREATE DATA GRANT` | Authorizes `SELECT/UPDATE/INSERT/DELETE` on an object, optionally narrowed by a `WHERE` predicate and a column list. Additive, and **default-deny**. |
| **Data role** | `CREATE DATA ROLE` | Maps to a role in external IAM (OCI IAM, Entra ID) or is managed locally in the database. |
| **End user** | `CREATE END USER` | An application user that owns no schema. These are the workshop's personas. |
| **Application identity** | `CREATE APPLICATION IDENTITY` | The agent or app itself, mapped to its OAuth client identifier. |
| **End-user security context** | driver-attached payload | Carries the acting identity per request. |
| **Access-check functions** | `ORA_IS_COLUMN_AUTHORIZED`, `ORA_CHECK_DATA_PRIVILEGE` | Let a query reason about its own permissions. |

Example — an analyst scoped to two regions, with amounts withheld:

```sql
CREATE DATA ROLE eda_analyst_east_role;
CREATE END USER analyst_east IDENTIFIED BY "...";
GRANT DATA ROLE eda_analyst_east_role TO analyst_east;

-- rows: EUROPE + MIDDLE_EAST only
CREATE OR REPLACE DATA GRANT eda_analyst_east_transactions AS
    SELECT ON FINANCE.TRANSACTIONS
    WHERE region IN ('EUROPE', 'MIDDLE_EAST')
    TO eda_analyst_east_role;

-- columns: this grant omits amount_cents, so it is returned as NULL
CREATE OR REPLACE DATA GRANT eda_analyst_east_customers AS
    SELECT (customer_id, full_name, email) ON FINANCE.CUSTOMERS
    WHERE customer_id IN (...)
    TO eda_analyst_east_role;
```

The client then attaches an identity instead of trusting itself:

```python
ctx = oracledb.create_end_user_security_context(
    end_user_identity=("ANALYST_EAST", key),
    database_access_token=token,                 # OBO or client-credentials
    data_roles=["EDA_ANALYST_EAST_ROLE"],
)
conn.set_end_user_security_context(ctx)
```

Local end users are unquoted DB identifiers. A UPN belongs in the external-authenticator clause
(`AND FACTOR 'oma_push' AS 'analyst.east@meridianbank.example'`), and OCI IAM deployments grant the
memory-store policies to `OciGroupPrincipal`s rather than local end users.

The agent no longer has to be trusted. It can emit the broadest SQL it likes; the kernel returns the
rows its end user is entitled to and nothing else.

## What this exercise database can actually do

Deep Sec is an **Enterprise-class** feature. The workshop runs **Oracle AI Database 26ai Free** in a
container, where it is absent. Measured on the live database:

```
release            : Oracle AI Database 26ai Free Release 23.26.1.0.0
DBMS_DEEP_SEC      : ABSENT
data-grant views   : ABSENT        (no DBA_DATA_GRANTS / DBA_DATA_ROLES / DBA_END_USERS)
DBMS_RLS           : present
OAMP               : 26.8.0
OAMP memory DDS    : available as an API, not enforceable on Free
=> enforcement     : VPD
```

and every Deep Sec DDL form is rejected with `ORA-00901 (invalid CREATE command)`:

| Statement | Result on 26ai Free |
|---|---|
| `CREATE DATA ROLE eda_probe_role` | `ORA-00901` |
| `CREATE END USER eda_probe_user` | `ORA-00901` |
| `CREATE DATA GRANT ... AS SELECT ...` | `ORA-00901` |
| `CREATE DATA SECURITY POLICY ... USING (1=1)` | `ORA-00901` |

Note the last row: even the earlier `CREATE DATA SECURITY POLICY` form is unavailable, so the
declarative branch in `app/scripts/setup_advanced.py` **always** falls through to its `DBMS_RLS`
fallback on this image.

## Two backends, one rule set

`app/backend/db/deep_security.py` probes the database and drives the strongest available backend.
`api/identities.py` stays the single source of truth, so the dropdown, the SQL tool, the Data
Explorer and the kernel cannot drift apart.

| | `DEEP_SEC` | `VPD` (this repo, on Free) | `APP_ONLY` |
|---|---|---|---|
| **Requires** | 26ai Enterprise-class (Base DB, Exadata, Autonomous AI Database) + IAM tokens | 26ai Free and older, `DBMS_RLS` | nothing |
| **Rows** | `CREATE DATA GRANT ... WHERE <predicate>` | `DBMS_RLS.ADD_POLICY` + application context | Python drops rows after fetch |
| **Columns** | omitted columns return `NULL` | `sec_relevant_cols` + `ALL_ROWS` returns `NULL` | Python overwrites with `[REDACTED]` |
| **Default** | default-deny | **fail-open** without a context | fail-open |
| **Trust boundary** | the kernel | the kernel | the application |

### How the VPD backend is wired

```
AGENT.agent_authorizations   end_user -> auth_region          (ALL means every region)
AGENT.agent_clearances       end_user -> clearance
AGENT.agent_masks            end_user -> owner.table.column   (columns to blank)
AGENT.agent_denials          end_user -> owner.table          (tables to refuse)
AGENT.agent_scope            end_user -> branch/account/customer keys (precomputed)
        |
        v
AGENT.set_eda_ctx(:end_user)   the ONLY writer of the EDA_CTX namespace
        |
        v
EDA_REGION_PREDICATE   EDA_SCOPE_PREDICATE   EDA_DENY_PREDICATE   EDA_MASK_<table>_<col>
        |
        v
15 DBMS_RLS policies on FINANCE
```

Three lessons are baked into that shape:

1. **The context setter is trusted.** Only `AGENT.set_eda_ctx` may write `EDA_CTX`, so a caller
   cannot simply declare itself the CFO. It derives clearance from `agent_clearances`.
2. **A predicate may not subquery another policied table.** Nesting `SELECT ... FROM
   FINANCE.branches` inside a policy on `FINANCE.accounts` raises `ORA-28113` at query time, because
   `branches` carries its own policy. Hence `agent_scope`: the reachable keys are precomputed and the
   predicate is a plain `EXISTS` against an unprotected table.
3. **Each masked column needs its own predicate function.** `DBMS_RLS` binds `sec_relevant_cols`
   into the *policy*, not into the function signature, so the function cannot see which column
   triggered it.

## Prove it

```bash
cd app && python scripts/setup_deep_security.py --demo
```

```
persona              clearance  transactions regions              amount  SAR rows   balance
--------------------------------------------------------------------------------------------
agent                STANDARD          23606 AMER,APAC,EU,ME        NULL         0      NULL
cfo                  EXECUTIVE         23606 AMER,APAC,EU,ME     visible         0   visible
compliance.officer   EXECUTIVE         23606 AMER,APAC,EU,ME     visible       117   visible
analyst.east         STANDARD           9697 EU,ME                  NULL         0      NULL
analyst.west         STANDARD          13909 AMER,APAC              NULL         0      NULL
ops.viewer           STANDARD          23606 AMER,APAC,EU,ME        NULL         0      NULL
--------------------------------------------------------------------------------------------
NULL means masked, not empty: the row came back, the value did not.
SAR rows = 0 for every persona except compliance.officer (default-deny).

  -- agent memory store (OAMP >= 26.8 Deep Data Security)
  not enforceable on backend=VPD: no data roles/data grants for the memory tables.
```

One `SELECT`, six personas, no application-layer filtering anywhere on the path. `NULL` means
*masked*, not empty: the row came back, the value did not. The memory section is the honest
Free result for the OAMP layer added above: the API is present and probed, the data roles it
needs are not.

The full matrix — every table × every persona — with an independent check:

| persona | transactions | branches | merchants | accounts | loans | cards | customers | SAR |
|---|---|---|---|---|---|---|---|---|
| agent | 23,606 | 60 | 140 | 2,650 | 900 | 2,984 | 2,000 | 0 |
| cfo | 23,606 | 60 | 140 | 2,650 | 900 | 2,984 | 2,000 | 0 |
| compliance.officer | 23,606 | 60 | 140 | 2,650 | 900 | 2,984 | 2,000 | **117** |
| analyst.east | 9,697 | 25 | 56 | 1,102 | 350 | 1,228 | 987 | 0 |
| analyst.west | 13,909 | 35 | 84 | 1,548 | 550 | 1,756 | 1,294 | 0 |
| ops.viewer | 23,606 | 60 | 140 | 2,650 | 900 | 2,984 | **0** | 0 |

## Where it is wired into the app

The kernel layer only matters if every read path drives it. `AGENT.SET_EDA_CTX` was previously
referenced *only* by the installer, which meant `SYS_CONTEXT('EDA_CTX','END_USER')` was always `NULL`
during real requests and the installed policies evaluated to `1=1`. Both read paths now set the
context before executing:

- [`app/backend/agent/tools.py`](../../app/backend/agent/tools.py) — `tool_run_sql`, so SQL the model
  composes is gated by the kernel
- [`app/backend/api/data_routes.py`](../../app/backend/api/data_routes.py) — the Data Explorer's rows
  endpoint

The Python post-filters stay in place as defence in depth and become no-ops when the database has
already answered correctly.

The notebook has no identity section; the app drives this boundary (persona selector, `AGENT.SET_EDA_CTX` before each read). The notebook never filters rows itself.
`tool_run_sql` in the app adds the one production rule the notebook does not need: every call
borrows a private READ ONLY `AGENT` session (`db.deep_security.identity_session`), sets the
context from the request's end user on it, and rolls back and clears it on release.

> ⚠️ **Two honest caveats.**
> 1. **The VPD path is fail-open.** With no context set, every predicate evaluates to `1=1` and all
>    rows are visible. Deep Sec is default-deny. That is the single biggest behavioural difference
>    between what this repo demonstrates and what the feature provides.
> 2. **The shared connection is never used for identity reads.** `EDA_CTX` lives in the database
>    session, so setting a persona on the app's one shared `AGENT` connection would let concurrent
>    requests overwrite each other's persona. `identity_session` instead hands each call one of a
>    semaphore-bounded pool (8) of private sessions; one that cannot be proven clean is dropped, not reused.

## Agent memory is data too — OAMP 26.8 Deep Data Security

Parts 2–7 store a great deal in the `AGENT` schema: every tool output, scanned schema fact, extracted
preference, and episodic turn lands in the OAMP-managed `EDA_ONNX_*` tables. That store contains the
same class of content as `FINANCE` — and until OAMP 26.8 it was protected only by application-level
thread and user scoping. `SELECT * FROM agent.eda_onnx_memory` returned every user's memories to
whoever held the connection.

`oracleagentmemory` 26.8 closes that gap with the same database-native model this part argues for.
The release adds four surfaces to the SDK:

| Surface | What it does |
|---|---|
| `UserOwnRowsDeepDataSecurityPolicy` | row-scoped `SELECT`, column-scoped `INSERT`/`UPDATE`, row-scoped `DELETE` on the end user's own memory rows (ownership, record type, and generated columns are immutable after insert; chunks are replaced, not updated) |
| `GlobalMemoriesDeepDataSecurityPolicy` | read access to unscoped (`user_id IS NULL`) memories plus links whose endpoints are both visible |
| `add_deep_data_security_policies` · `grant_agent_memory_policies` · `list_*` · `remove_*` · `revoke_*` | administration API — creates the data roles and data grants for one `owner_schema` + `memory_store_id`, then assigns them to `LocalEndUserPrincipal` or `OciGroupPrincipal` grantees |
| `OracleMemoryEndUserSecurityContext` | runtime context manager that attaches the end user to every OAMP operation (sync and async), verifies the identity on the acquired connection, and clears it before release; background extraction keeps a private snapshot |

The policy internals — managed tables, roles, grants, SQL — stay private to the SDK and may change
between releases. That is why the workshop installs them through the API instead of hand-writing DDL:

```python
from oracleagentmemory.core.deepsec import (
    GlobalMemoriesDeepDataSecurityPolicy,
    LocalEndUserPrincipal,
    UserOwnRowsDeepDataSecurityPolicy,
    add_deep_data_security_policies,
    grant_agent_memory_policies,
)

policies = [UserOwnRowsDeepDataSecurityPolicy(),
            GlobalMemoriesDeepDataSecurityPolicy()]

add_deep_data_security_policies(
    sys_conn, owner_schema="AGENT", memory_store_id="EDA_ONNX", policies=policies)

for persona in IDENTITIES.values():
    grant_agent_memory_policies(
        sys_conn, memory_store_id="EDA_ONNX", owner_schema="AGENT",
        principals=[LocalEndUserPrincipal(local_end_user_name(persona.id))],
        policies=policies)
```

`local_end_user_name()` maps `analyst.east` to the unquoted identifier `ANALYST_EAST`; the OAMP 26.8
API rejects `LocalEndUserPrincipal` names containing `.` or `@`, and an OCI IAM deployment would pass
`OciGroupPrincipal("<group>")` instead.

At runtime the identity travels with the call, not with a session variable:

```python
ctx = oracledb.create_end_user_security_context(
    end_user_identity=("ANALYST_EAST", key),
    database_access_token=token,
)
with OracleMemoryEndUserSecurityContext(ctx):
    thread.add_messages(messages)          # the kernel filters the memory rows
```

`db/deep_security.py` owns all of this in the workshop: `probe()` now reports `oamp=<version>` and
`memory_deep_sec`, `install_memory_policies()` / `list_memory_policies()` drive the admin API and
return a report, and `memory_end_user_context(ctx)` is the runtime wrapper.
`scripts/setup_deep_security.py` runs the install as part of its enforcement step and prints the
result under `--demo`.

### What changed in the workshop

- **The floor is `oracleagentmemory>=26.8`** (was `>=26.4`) in both `requirements.txt` files.
- **The OAMP client now uses `memory_store_id="EDA_ONNX"`** instead of the deprecated
  `table_name_prefix="eda_onnx_"`. The two resolve to the same `EDA_ONNX_*` tables, so existing
  memories survive the upgrade; the prefix form is removed in OAMP 27.1.
- **Enforcement covers two stores**: `FINANCE` (data grants, or VPD on Free) and the OAMP
  memory store (OAMP-managed data grants).
- **Deep Sec end users are unquoted local identifiers** (`ANALYST_EAST`, not the quoted UPN form).
  `LocalEndUserPrincipal` in OAMP 26.8.0 requires a valid unquoted Oracle identifier; a UPN belongs
  in the external-authenticator clause, and OCI IAM deployments grant to `OciGroupPrincipal` instead.

### On the shipped Free container

The OAMP policies compile to `CREATE DATA ROLE` / `CREATE DATA GRANT` — exactly the statements 26ai
Free rejects with `ORA-00901` — so the installer reports the skip instead of pretending the memory
layer is protected:

```
  [memory] skipped AGENT.EDA_ONNX: backend=VPD has no data roles/data grants (OAMP memory policies require Deep Sec).
```

Nothing else changes on Free: thread scoping, provenance tags, and the harness's
`(user, agent, thread)` model remain the application-level boundary, and the fail-open caveat above
applies to them just as it does to `FINANCE`.

## Running it on a database that has Deep Sec

```bash
cd app && python scripts/setup_deep_security.py --ddl-only
```

This writes `app/scripts/out/deep_sec_ddl.sql` — 67 statements generated from the same persona
registry: 6 data roles, 6 unquoted local end users, 12 role grants (end user + application identity), 42 row
and column data grants, and the application identity itself. The file ends with the OAMP
memory-store policy sketch, because those roles and grants are created through the SDK, not by
this DDL. Reviewed by hand, the file is the migration.

> **Verification status.** The generated Deep Sec DDL is produced from the live schema but has **not**
> been executed, because no 26ai Enterprise-class instance is available to this repo. Everything in the
> `VPD` column of the tables above was executed and verified against the live container. The OAMP
> memory-policy path is gated the same way: the SDK call shapes (`add_deep_data_security_policies`,
> `grant_agent_memory_policies`, `OracleMemoryEndUserSecurityContext`) are verified against
> `oracleagentmemory` 26.8.0, and the Free-edition skip path is executed end to end.

## Where this is implemented

Nothing in this guide is generated into the notebook. The moving parts are:

```bash
python app/scripts/setup_deep_security.py   # installs/refreshes the policies, rules and predicates
```

- **App:** `app/backend/db/deep_security.py` (probe, VPD backend, Deep Sec DDL emitter),
  `app/backend/api/identities.py` (the persona registry) and `identity_session` in `deep_security.py`,
  which `tool_run_sql` and the Data Explorer use to set `EDA_CTX` per call.
- **DDL for an Enterprise-class instance:** `app/scripts/setup_deep_security.py --ddl-only` writes
  `app/scripts/out/deep_sec_ddl.sql`.

## Checklist for a real deployment

1. Run `setup_deep_security.py --ddl-only` and review `deep_sec_ddl.sql`.
2. Register the database as an OAuth resource in OCI IAM or Entra ID; register the agent as an OAuth
   client with a client-credentials grant.
3. Execute the DDL on the target. End users are unquoted local identifiers; for OCI IAM/UPN
   identities, keep the UPN as the external-authenticator name and grant the OAMP memory policies to
   `OciGroupPrincipal`s instead of `LocalEndUserPrincipal`s.
4. Replace the `VPD` backend in `db/deep_security.py::set_identity` by attaching an
   `EndUserSecurityContext` per request. The persona-to-data-role mapping is already there.
5. Install the OAMP memory-store policies on the target (`install_memory_policies()`, or just re-run
   `setup_deep_security.py` there) and wrap runtime memory calls in
   `memory_end_user_context(ctx)` / `OracleMemoryEndUserSecurityContext`.
6. Add an audit of which sessions set a context, then remove the Python post-filters — they should be
   redundant.
7. Prefer `ORA_IS_COLUMN_AUTHORIZED` over a blank cell in the UI, so a masked value renders as a
   deliberate mask rather than an empty field.
