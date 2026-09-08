# JSON Duality Views

The advanced-tier feature most worth showing off. One physical schema, two equally-live views: nested JSON for the agent, flat relational rows for the dashboard. No ETL, no sync job, no eventual consistency — both views are the *same data*.

## When to use

The use case the advanced skill scaffolds verbatim: **a code-review agent that writes nested JSON reviews and lets a dashboard query `GROUP BY severity`**. The agent likes JSON because LLMs produce it natively. The dashboard likes rows because BI is row-shaped. Duality views give you both for free.

Generalize: any time the *write path* wants nested documents and the *read path* wants relational analytics, this beats both:
- Storing JSON in a CLOB and using `JSON_VALUE` for analytics (slow, no indexes by default).
- Storing relational and assembling JSON in the app (boilerplate, drift).

## The worked example

Three relational tables, one duality view that exposes them as a single document.

```sql
CREATE TABLE review (
    review_id  NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repo       VARCHAR2(200) NOT NULL,
    sha        VARCHAR2(40)  NOT NULL,
    reviewed_at TIMESTAMP    DEFAULT SYSTIMESTAMP NOT NULL
);

CREATE TABLE review_file (
    file_id    NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    review_id  NUMBER NOT NULL REFERENCES review(review_id),
    path       VARCHAR2(500) NOT NULL
);

CREATE TABLE review_finding (
    finding_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    file_id    NUMBER NOT NULL REFERENCES review_file(file_id),
    severity   VARCHAR2(20) NOT NULL,
    line_no    NUMBER,
    msg        VARCHAR2(2000) NOT NULL
);

CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW review_dv AS
SELECT JSON {
    'review_id' : r.review_id,
    'repo'      : r.repo,
    'sha'       : r.sha,
    'reviewed_at' : r.reviewed_at,
    'files' : [
        SELECT JSON {
            'path' : f.path,
            'findings' : [
                SELECT JSON {
                    'severity' : fd.severity,
                    'line'     : fd.line_no,
                    'msg'      : fd.msg
                }
                FROM review_finding fd WITH INSERT UPDATE DELETE
                WHERE fd.file_id = f.file_id
            ]
        }
        FROM review_file f WITH INSERT UPDATE DELETE
        WHERE f.review_id = r.review_id
    ]
}
FROM review r WITH INSERT UPDATE DELETE;
```

The `WITH INSERT UPDATE DELETE` annotations on each table tell Oracle: writes through the view propagate to this table. Drop one annotation and that level becomes read-only through the view.

## Two equally-live access patterns

### Agent (nested JSON)

```python
import oracledb, json

review = {
    "repo": "user/myproj",
    "sha": "abc123",
    "files": [
        {"path": "auth.py", "findings": [{"severity": "high", "line": 42, "msg": "..."}]},
        {"path": "db.py",   "findings": [{"severity": "low",  "line": 12, "msg": "..."}]},
    ],
}
with conn.cursor() as cur:
    cur.execute("INSERT INTO review_dv (data) VALUES (:doc)", doc=json.dumps(review))
    conn.commit()
```

The agent writes one document. Oracle splits it into rows across `review`, `review_file`, `review_finding`.

Reading the same way:

```python
cur.execute("SELECT JSON_SERIALIZE(data RETURNING CLOB) FROM review_dv WHERE review_id = :id", id=1)
doc = json.loads(cur.fetchone()[0])
```

### Dashboard (flat relational)

```sql
SELECT severity, COUNT(*) AS n
FROM review_finding
GROUP BY severity
ORDER BY n DESC;
```

```sql
SELECT f.path, COUNT(*) AS n_findings
FROM review_file f
JOIN review_finding fd ON fd.file_id = f.file_id
GROUP BY f.path
ORDER BY n_findings DESC
FETCH FIRST 10 ROWS ONLY;
```

No ETL job. The agent's last write is visible to the dashboard immediately.

## Constraints

| Constraint | What | Implication |
| --- | --- | --- |
| **No composite keys.** | Each underlying table needs a single-column primary key. | Plan the schema accordingly. Add a synthetic `id` if needed. |
| **Identity / sequence-generated PKs preferred.** | Avoids the user having to mint IDs in the JSON document. | The schema above uses `GENERATED ALWAYS AS IDENTITY`. |
| **Nesting depth.** | Two levels nest cleanly (review → files → findings). Three+ often need hand-tuning. | Don't over-nest just because JSON allows it. |
| **`WITH INSERT UPDATE DELETE` is per-table-per-direction.** | Forget it on a child table → that child is read-only via the view. | The advanced skill always annotates all three. |

## What the advanced skill scaffolds

For project idea #2 (code-review agent):

- The three tables above, in `migrations/001_review_schema.sql`.
- The `review_dv` duality view, in `migrations/002_review_dv.sql`.
- An agent that writes nested JSON via `review_dv`.
- A Gradio dashboard tab that runs the relational analytics queries.
- Tests that write through the agent path and read through the dashboard path *in the same transaction* to prove duality.

## Don't do these

- Don't store the same field both inside the JSON and in a separate column "for query performance." Duality views *are* the query performance layer.
- Don't try to make the duality view writable through joins of unrelated tables. It's hierarchical, not arbitrary.
- Don't skip the `WITH INSERT UPDATE DELETE` annotations. Default is read-only, not writable.

## Exemplar

`~/git/work/demoapp/api/app/routers/json_views.py:1-80` — `inspection_report_dv` with the same parent / child / grandchild shape. Different domain (inspections instead of reviews), same pattern.

## Canonical doc

https://docs.oracle.com/en/database/oracle/oracle-database/26/jsnvu/
