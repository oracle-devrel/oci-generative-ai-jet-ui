"""Tool & skill registries (DB-backed, embedding-retrieved), automations, and the
domain 'doer' tools the agent calls. Mirrors the notebook's Part 6."""
from __future__ import annotations

import hashlib
import json
import re

import requests

from backend.core import db, memory, scratch

EMB = db.EMB
TOOLS: dict = {}  # name -> callable (callables can't live in the DB)


# ── tool registry ──────────────────────────────────────────────────────────
def register_tool(
    name,
    fn,
    description,
    params,
    *,
    category="general",
    synonyms=None,
    examples=None,
    when_to_use="",
):
    schema = {"name": name, "description": description, "parameters": params}
    TOOLS[name] = fn
    enriched = (
        f"TOOL {name}: {description}\ncategory: {category}\n"
        f"synonyms: {', '.join(synonyms or [])}\nuse when: {when_to_use}\n"
        f"examples: {' | '.join(examples or [])}"
    )
    db.x(
        f"""MERGE INTO agent_tools d USING (SELECT :n AS name FROM dual) s ON (d.name=s.name)
        WHEN MATCHED THEN UPDATE SET description=:d, category=:c, tool_schema=:sc,
            embedding=VECTOR_EMBEDDING({EMB} USING :doc AS DATA)
        WHEN NOT MATCHED THEN INSERT (name, description, category, tool_schema, embedding)
            VALUES (:n,:d,:c,:sc, VECTOR_EMBEDDING({EMB} USING :doc AS DATA))""",
        {"n": name, "d": description, "c": category, "sc": json.dumps(schema), "doc": enriched},
    )


def retrieve_tools(query, k=6):
    return db.q(
        f"""SELECT name, description, tool_schema,
                VECTOR_DISTANCE(embedding, VECTOR_EMBEDDING({EMB} USING :q AS DATA), COSINE) dist
                FROM agent_tools ORDER BY dist FETCH APPROX FIRST :k ROWS ONLY""",
        {"q": query, "k": k},
    )


def get_tool_schema(name):
    r = db.q("SELECT tool_schema FROM agent_tools WHERE name=:n", {"n": name})
    return r[0]["TOOL_SCHEMA"] if r else None


# ── doer tools ──────────────────────────────────────────────────────────────
def list_sources():
    rows = db.q(
        "SELECT table_name FROM user_tables WHERE table_name IN "
        "('CUSTOMERS','PRODUCTS','ORDERS','ORDER_ITEMS') ORDER BY table_name"
    )
    return [r["TABLE_NAME"] for r in rows] + ["V_REVENUE (view)"]


_FORBIDDEN = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|MERGE|GRANT|CREATE)\b", re.I)


def run_sql(sql, max_rows=100):
    if ";" in sql.strip().rstrip(";"):
        return {"error": "one statement only"}
    if not sql.strip().upper().startswith(("SELECT", "WITH")):
        return {"error": "SELECT/WITH only"}
    if _FORBIDDEN.search(sql):
        return {"error": "write/DDL keyword rejected"}
    try:
        return {"rows": db.q(sql)[:max_rows]}
    except Exception as e:
        return {"error": str(e).splitlines()[0]}


def author_materialized_view(name, select_sql):
    chk = run_sql(select_sql, max_rows=1)
    if "error" in chk:
        return {"error": "select failed: " + chk["error"]}
    db.ddl(f"DROP MATERIALIZED VIEW {name}")
    db.ddl(
        f"CREATE MATERIALIZED VIEW {name} BUILD IMMEDIATE REFRESH COMPLETE ON DEMAND AS {select_sql}"
    )
    return {"created": name}


def _job(job, action, repeat):
    try:
        db.x("BEGIN DBMS_SCHEDULER.DROP_JOB(:n, force=>TRUE); END;", {"n": job})
    except Exception:
        pass
    db.x(
        """BEGIN DBMS_SCHEDULER.CREATE_JOB(job_name=>:n, job_type=>'PLSQL_BLOCK',
            job_action=>:a, repeat_interval=>:r, enabled=>TRUE); END;""",
        {"n": job, "a": action, "r": repeat},
    )


def create_automation(name, select_sql, cadence_hours=24, description=""):
    try:
        cadence_hours = int(float(cadence_hours))
    except Exception:
        cadence_hours = 24
    name = re.sub(r"[^A-Za-z0-9_]", "_", name).strip("_").lower() or "automation"
    mv, job = f"MV_{name.upper()}", f"AUTO_{name.upper()}_JOB"
    res = author_materialized_view(mv, select_sql)
    if "error" in res:
        return res
    _job(
        job, f"BEGIN DBMS_MVIEW.REFRESH('{mv}', 'C'); END;", f"FREQ=HOURLY;INTERVAL={cadence_hours}"
    )
    db.x("DELETE FROM agent_automations WHERE name=:n", {"n": name})
    db.x(
        """INSERT INTO agent_automations (name, description, artifact, job_name, cadence_hours, select_sql)
            VALUES (:n,:d,:a,:j,:c,:s)""",
        {"n": name, "d": description, "a": mv, "j": job, "c": cadence_hours, "s": select_sql},
    )
    memory.capture_workflow(
        f"build automation {name}: {description}",
        [
            {"step": "author_select"},
            {"step": "materialize", "mv": mv},
            {"step": "schedule", "job": job},
        ],
        ["author_materialized_view", "create_automation"],
    )
    return {"automation": name, "artifact": mv, "job": job, "cadence_hours": cadence_hours}


def list_automations():
    return db.q(
        "SELECT name, artifact, job_name, cadence_hours, description FROM agent_automations ORDER BY created_at"
    )


def automation_status():
    """Automations joined with their live DBMS_SCHEDULER state (enabled, last/next run)."""
    return db.q(
        """SELECT a.name, a.artifact, a.job_name, a.cadence_hours, a.description,
        NVL(j.enabled,'FALSE') AS enabled, j.state,
        TO_CHAR(j.last_start_date,'YYYY-MM-DD HH24:MI') AS last_run,
        TO_CHAR(j.next_run_date,'YYYY-MM-DD HH24:MI') AS next_run
        FROM agent_automations a
        LEFT JOIN user_scheduler_jobs j ON j.job_name = a.job_name
        ORDER BY a.created_at"""
    )


def run_automation_now(name):
    """Refresh the automation's materialized view now and return its latest rows."""
    r = db.q("SELECT artifact FROM agent_automations WHERE name=:n", {"n": name})
    if not r:
        return {"error": "no such automation"}
    mv = r[0]["ARTIFACT"]
    try:
        db.x(f"BEGIN DBMS_MVIEW.REFRESH('{mv}', 'C'); END;")
        return {"refreshed": mv, "rows": db.q(f"SELECT * FROM {mv} FETCH FIRST 20 ROWS ONLY")}
    except Exception as e:
        return {"error": str(e).splitlines()[0]}


def toggle_automation(name, enable=True):
    """Start (enable) or stop (disable) an automation's scheduled job."""
    r = db.q("SELECT job_name FROM agent_automations WHERE name=:n", {"n": name})
    if not r:
        return {"error": "no such automation"}
    job = r[0]["JOB_NAME"]
    try:
        if enable:
            db.x("BEGIN DBMS_SCHEDULER.ENABLE(:j); END;", {"j": job})
        else:
            db.x("BEGIN DBMS_SCHEDULER.DISABLE(:j, force=>TRUE); END;", {"j": job})
        return {"name": name, "enabled": bool(enable)}
    except Exception as e:
        return {"error": str(e).splitlines()[0]}


def automation_results(name, k=20):
    r = db.q("SELECT artifact FROM agent_automations WHERE name=:n", {"n": name})
    if not r:
        return {"error": "no such automation"}
    try:
        return {
            "artifact": r[0]["ARTIFACT"],
            "rows": db.q(f"SELECT * FROM {r[0]['ARTIFACT']} FETCH FIRST :k ROWS ONLY", {"k": k}),
        }
    except Exception as e:
        return {"error": str(e).splitlines()[0]}


def promote_file_to_memory(path):
    try:
        text = scratch.read(path)
    except Exception as e:
        return {"error": str(e)}
    memory.remember(text)
    db.x("UPDATE agent_scratch SET promoted='Y' WHERE path=:p", {"p": scratch._abs(path)})
    return {"promoted": path}


# ── skill registry ──────────────────────────────────────────────────────────
def _skill_md(name, description, tools, body):
    return (
        f"---\nname: {name}\ndescription: {description}\ntools: {', '.join(tools)}\n---\n\n"
        f"## When to use\n{description}\n\n## Steps\n{body}\n"
    )


def save_skill(name, description, skill_md, tools_used, source_workflow_id=None, source_url=None):
    sha = hashlib.sha256(skill_md.encode("utf-8")).hexdigest()
    db.x(
        f"""MERGE INTO agent_skills d USING (SELECT :n AS name FROM dual) s ON (d.name=s.name)
        WHEN MATCHED THEN UPDATE SET description=:d, sha=:sha, source_url=:url, skill_md=:b,
            tools_used=:t, source_workflow_id=:w, updated_at=SYSTIMESTAMP,
            embedding=VECTOR_EMBEDDING({EMB} USING :emb AS DATA)
        WHEN NOT MATCHED THEN INSERT (name, description, sha, source_url, skill_md, tools_used, source_workflow_id, embedding)
            VALUES (:n,:d,:sha,:url,:b,:t,:w, VECTOR_EMBEDDING({EMB} USING :emb AS DATA))""",
        {
            "n": name,
            "d": description,
            "sha": sha,
            "url": source_url,
            "b": skill_md,
            "t": ",".join(tools_used or []),
            "w": source_workflow_id,
            "emb": f"{name}: {description}",
        },
    )
    return sha


def retrieve_skills(query, k=5):
    return db.q(
        f"""SELECT name, description, sha, source_url,
                VECTOR_DISTANCE(embedding, VECTOR_EMBEDDING({EMB} USING :q AS DATA), COSINE) dist
                FROM agent_skills ORDER BY dist FETCH APPROX FIRST :k ROWS ONLY""",
        {"q": query, "k": k},
    )


def build_skill_manifest(query, k=5):
    rows = retrieve_skills(query, k=k)
    return "\n".join(f"- {r['NAME']}: {r['DESCRIPTION']}" for r in rows) or "(no skills yet)"


def load_skill(name):
    r = db.q(
        "SELECT name, description, skill_md, tools_used, sha, source_url FROM agent_skills WHERE name=:n",
        {"n": name},
    )
    return r[0] if r else {"error": "no such skill"}


def promote_workflow_to_skill(workflow_id):
    wf = db.q(
        "SELECT RAWTOHEX(id) id, intent, steps, tools_used FROM agent_workflow WHERE RAWTOHEX(id)=:i",
        {"i": workflow_id.upper()},
    )
    if not wf:
        return {"error": "no such workflow"}
    wf = wf[0]
    tools = [t for t in (wf["TOOLS_USED"] or "").split(",") if t]
    name = (wf["INTENT"][:40] or "skill").strip().replace(" ", "_").lower()
    desc, body = f"Reusable playbook for: {wf['INTENT']}", str(wf["STEPS"])
    try:
        from backend.core.anthropic_client import MODEL, client, text_of

        out = text_of(
            client.messages.create(
                model=MODEL,
                max_tokens=512,
                messages=[
                    {
                        "role": "user",
                        "content": f"Distil into a skill. Intent: {wf['INTENT']}. Steps: {wf['STEPS']}. "
                        'Return JSON {"name":"snake","description":"one line","body":"numbered markdown steps"}.',
                    }
                ],
            )
        )
        spec = json.loads(out[out.find("{") : out.rfind("}") + 1])
        name, desc, body = spec["name"], spec["description"], spec["body"]
    except Exception:
        pass
    md = _skill_md(name, desc, tools, body)
    save_skill(name, desc, md, tools, source_workflow_id=bytes.fromhex(wf["ID"]))
    db.x("UPDATE agent_workflow SET promoted='Y' WHERE RAWTOHEX(id)=:i", {"i": wf["ID"]})
    return {"promoted_skill": name, "skill_md": md}


def harvest_skills(min_occurrences=3, recency_days=30):
    cands = db.q(
        """SELECT RAWTOHEX(id) id FROM agent_workflow
        WHERE promoted='N' AND occurrences >= :m AND last_seen >= SYSTIMESTAMP - :d ORDER BY occurrences DESC""",
        {"m": min_occurrences, "d": recency_days},
    )
    return [promote_workflow_to_skill(c["ID"]).get("promoted_skill") for c in cands]


def _fetch_skill_text(src):
    if src.startswith("http"):
        return requests.get(src, timeout=30).text
    if src.startswith(scratch.MOUNT):
        return scratch.read(src)
    with open(src) as f:
        return f.read()


def _parse_frontmatter(text):
    name = desc = None
    m = re.search(r"^---\s*\n(.*?)\n---", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            low = line.lower()
            if low.startswith("name:"):
                name = line.split(":", 1)[1].strip()
            elif low.startswith("description:"):
                desc = line.split(":", 1)[1].strip()
    return name, desc


def register_skill_from_source(src):
    text = _fetch_skill_text(src)
    name, desc = _parse_frontmatter(text)
    name = (name or src.rsplit("/", 1)[-1].replace(".md", "")).strip().replace(" ", "_").lower()
    sha = save_skill(name, desc or "(imported skill)", text, [], source_url=src)
    return {"skill": name, "sha": sha[:12], "source": src}


def refresh_skills_from_source():
    updated = []
    for r in db.q("SELECT name, sha, source_url FROM agent_skills WHERE source_url IS NOT NULL"):
        try:
            text = _fetch_skill_text(r["SOURCE_URL"])
            if hashlib.sha256(text.encode("utf-8")).hexdigest() != r["SHA"]:
                name, desc = _parse_frontmatter(text)
                save_skill(
                    name or r["NAME"], desc or "(updated)", text, [], source_url=r["SOURCE_URL"]
                )
                updated.append(r["NAME"])
        except Exception:
            pass
    return updated


# ── registration ────────────────────────────────────────────────────────────
def register_default_tools():
    register_tool(
        "list_sources",
        lambda: list_sources(),
        "List queryable tables/views in the analytics schema.",
        {},
        category="explore",
        synonyms=["schema", "tables"],
        when_to_use="before writing SQL",
    )
    register_tool(
        "run_sql",
        lambda sql: run_sql(sql),
        "Run a read-only SELECT and return rows.",
        {"sql": "string"},
        category="data",
        synonyms=["query", "analyze"],
        when_to_use="to answer an analytical question",
    )
    register_tool(
        "create_automation",
        lambda name, select_sql, cadence_hours=24, description="": create_automation(
            name, select_sql, cadence_hours, description
        ),
        "Promote a SELECT into a scheduled, refreshed materialized view.",
        {
            "name": "string",
            "select_sql": "string",
            "cadence_hours": "number",
            "description": "string",
        },
        category="automation",
        synonyms=["schedule", "recurring", "daily report"],
    )
    register_tool(
        "search_memory",
        lambda query: memory.recall(query),
        "Search durable long-term memory by meaning.",
        {"query": "string"},
        category="memory",
    )
    register_tool(
        "recall_workflow",
        lambda query: memory.recall_workflow(query),
        "Recall a proven workflow recipe before building.",
        {"query": "string"},
        category="memory",
    )
    register_tool(
        "find_skill",
        lambda query: build_skill_manifest(query),
        "List relevant skills (the level-1 manifest).",
        {"query": "string"},
        category="skills",
    )
    register_tool(
        "load_skill",
        lambda name: load_skill(name),
        "Load a skill's full SKILL.md body.",
        {"name": "string"},
        category="skills",
    )
    register_tool(
        "list_automations",
        lambda: automation_status(),
        "List existing automations with their schedule state.",
        {},
        category="automation",
    )
    register_tool(
        "toggle_automation",
        lambda name, enable=True: toggle_automation(name, enable),
        "Start (enable) or stop (disable) an automation's schedule.",
        {"name": "string", "enable": "boolean"},
        category="automation",
        synonyms=["start", "stop", "pause", "resume", "enable", "disable"],
    )
    register_tool(
        "run_automation_now",
        lambda name: run_automation_now(name),
        "Refresh an automation now and return its latest rows.",
        {"name": "string"},
        category="automation",
        synonyms=["refresh", "run now", "execute"],
    )
    register_tool(
        "remember_fact",
        lambda fact: (memory.remember(fact), {"saved": fact[:60]})[1],
        "Save a durable fact to long-term memory.",
        {"fact": "string"},
        category="memory",
    )
    register_tool(
        "promote_file_to_memory",
        lambda path: promote_file_to_memory(path),
        "Promote a scratch file into durable long-term memory.",
        {"path": "string"},
        category="memory",
    )


def seed_starter_skills():
    if db.q("SELECT COUNT(*) n FROM agent_skills")[0]["N"] > 0:
        return
    save_skill(
        "revenue_by_category",
        "Compute net revenue grouped by product category over a recent window",
        _skill_md(
            "revenue_by_category",
            "Compute net revenue by product category",
            ["list_sources", "run_sql", "create_automation"],
            "1. list_sources\n2. SELECT category, SUM(net_revenue) FROM v_revenue ... GROUP BY category\n"
            "3. optionally create_automation to refresh it on a cadence",
        ),
        ["list_sources", "run_sql", "create_automation"],
    )
