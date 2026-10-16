"""Plumbing for Part 4: tool registry, schema building, toolbox rows, memory tools, skills."""
import inspect
import itertools
import json
import typing

import oracledb

_PRIMS = {int: "integer", float: "number", bool: "boolean", str: "string"}


def _hint_to_json(hint):
    origin = typing.get_origin(hint)
    if hint in _PRIMS:
        return {"type": _PRIMS[hint]}
    if origin in (list, typing.List):
        args = typing.get_args(hint) or (str,)
        return {"type": "array", "items": _hint_to_json(args[0])}
    if origin in (dict, typing.Dict):
        return {"type": "object"}
    if origin is typing.Union:
        non_none = [a for a in typing.get_args(hint) if a is not type(None)]
        if len(non_none) == 1:
            return _hint_to_json(non_none[0])
    return {"type": "string"}


def build_schema(fn):
    """Turn a function into (name, description, parameters, openai_schema)."""
    raw_name = fn.__name__
    name = raw_name[5:] if raw_name.startswith("tool_") else raw_name
    description = (inspect.getdoc(fn) or "").strip()
    if not description:
        raise ValueError(f"tool {name!r} has no docstring; @register needs one for retrieval")
    sig = inspect.signature(fn)
    hints = typing.get_type_hints(fn)
    properties, required = {}, []
    for pname, param in sig.parameters.items():
        prop = _hint_to_json(hints.get(pname, str))
        if param.default is not inspect.Parameter.empty and param.default is not None:
            prop["default"] = param.default
        else:
            required.append(pname)
        properties[pname] = prop
    parameters = {"type": "object", "properties": properties, "required": required}
    return name, description, parameters, {
        "type": "function",
        "function": {"name": name, "description": description, "parameters": parameters},
    }


def upsert_toolbox_row(conn, embed_model, name, description, parameters):
    """MERGE one embedded row into toolbox."""
    embed_text = f"{name}: {description}\nargs: {' '.join(parameters['properties'].keys())}"
    with conn.cursor() as cur:
        cur.execute(
            "MERGE INTO toolbox t USING (SELECT :tn AS n FROM dual) s ON (t.name = s.n) "
            "WHEN MATCHED THEN UPDATE SET description = :td, parameters = :tp, "
            f" embedding = VECTOR_EMBEDDING({embed_model} USING :etext AS DATA), "
            " updated_at = CURRENT_TIMESTAMP "
            "WHEN NOT MATCHED THEN INSERT (name, description, parameters, embedding) "
            f" VALUES (:tn, :td, :tp, VECTOR_EMBEDDING({embed_model} USING :etext AS DATA))",
            tn=name, td=description, tp=json.dumps(parameters), etext=embed_text,
        )
    conn.commit()


def make_registry(conn, embed_model):
    """The tool registry: `(TOOLS, ALWAYS_ON_TOOLS, register)`.

    `@register` records a function in three places: the `TOOLS` dispatch table the agent loop
    calls, the schema shown to the model, and an embedded row in the `toolbox` table.
    """
    tools = {}
    always_on = {"search_knowledge", "run_sql", "remember", "load_skill"}

    def register(fn):
        name, description, parameters, schema = build_schema(fn)
        tools[name] = (fn, schema)
        upsert_toolbox_row(conn, embed_model, name, description, parameters)
        return fn

    return tools, always_on, register


def lob_text(value):
    """A CLOB/LOB column value as str."""
    return value.read() if hasattr(value, "read") else str(value or "")


def rows_json(cur, max_rows):
    """JSON string with the columns and at most `max_rows` rows of an executed cursor."""
    columns = [d[0] for d in cur.description]
    rows = [[lob_text(v) if hasattr(v, "read") else v for v in row]
            for row in itertools.islice(cur, max_rows)]
    return json.dumps({"columns": columns, "rows": rows, "row_count": len(rows)}, default=str)


def search_knowledge(retrieve_knowledge, query, k=5, kinds=None):
    """Run the retrieval ladder and return the hits as JSON, each body cut to 500 characters."""
    hits = retrieve_knowledge(query, k=k, kinds=kinds)
    for hit in hits:
        hit["body"] = hit["body"][:500]
    return json.dumps(hits)


def _find_memory(memory_client, user_id, agent_id, ref):
    hits = memory_client.search(ref, user_id=user_id, agent_id=agent_id,
                                max_results=1, include_invalid_results=False)
    return hits[0].record.id if hits else None


def remember(conn, memory_client, write_facts, fact_cls, user_id, agent_id,
             subject, body, kind="correction", supersedes=""):
    """Store a fact; when `supersedes` is given, link it to the memory it replaces."""
    old_id = None
    if supersedes:
        old_id = _find_memory(memory_client, user_id, agent_id, supersedes)
        if not old_id:
            return json.dumps({"ok": False, "error": f"no memory matched {supersedes!r}"})
    fact = fact_cls(kind=kind, subject=subject, body=body, metadata={"source": "agent_remember"})
    new, updated, _ = write_facts([fact])
    result = {"ok": True, "new": new, "updated": updated}
    if old_id:
        with conn.cursor() as cur:
            cur.execute("SELECT record_id FROM eda_onnx_memory WHERE metadata LIKE :p "
                        "ORDER BY created_at DESC FETCH FIRST 1 ROWS ONLY", p=f'%"{subject}"%')
            row = cur.fetchone()
        rel = memory_client._store.add_relations(
            source_record_ids=row[0], source_record_types="memory",
            target_record_ids=old_id, target_record_types="memory",
            relation_types="supersedes", metadata={})
        result.update({"retired_memory": old_id, "relation_id": rel[0] if rel else None})
    return json.dumps(result)


def link_memories(memory_client, user_id, agent_id, source, target, link_type="supports", reason=""):
    """Add a relation source -> target between two memories found by id or phrase."""
    source_id = _find_memory(memory_client, user_id, agent_id, source)
    target_id = _find_memory(memory_client, user_id, agent_id, target)
    if not source_id or not target_id:
        return json.dumps({"ok": False,
                           "error": f"no memory matched {source if not source_id else target!r}"})
    rel = memory_client._store.add_relations(
        source_record_ids=source_id, source_record_types="memory",
        target_record_ids=target_id, target_record_types="memory",
        relation_types=link_type, metadata={"reason": reason} if reason else {})
    return json.dumps({"ok": True, "relation_id": rel[0] if rel else None,
                       "link_type": link_type, "source_id": source_id, "target_id": target_id})


def load_skill(conn, name):
    """Read one skill (description, body, source) from the skillbox as JSON."""
    with conn.cursor() as cur:
        cur.execute("SELECT description, body, source_url, category FROM skillbox WHERE name = :n",
                    n=name)
        row = cur.fetchone()
    if not row:
        return json.dumps({"error": f"no skill named {name!r}"})
    desc, body, url, category = row
    return json.dumps({"name": name, "category": category, "description": desc,
                       "source_url": url, "body": lob_text(body)})


def skill_manifest(conn, embed_model, query, k=3):
    """One line per nearest skill, ready to prepend to the prompt ('' if none)."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT name, description FROM skillbox "
                f" ORDER BY VECTOR_DISTANCE(embedding, VECTOR_EMBEDDING({embed_model} USING :q AS DATA), COSINE) "
                " FETCH FIRST :k ROWS ONLY", q=query, k=k)
            rows = list(cur)
    except oracledb.DatabaseError:
        return ""
    if not rows:
        return ""
    lines = [f"  - {n} — {lob_text(d)[:240]}" for n, d in rows]
    return ("Available skills (call load_skill(name) to read the full guide and follow it):\n"
            + "\n".join(lines) + "\n\n")


def check_retrieve_tools(conn, register, tools, always_on, retrieve_tools):
    """Checkpoint for TODO 5: register two probe tools, check the retrieval, then remove them."""
    def tool_zz_currency(amount: float, currency: str) -> str:
        """Convert an amount between currencies using today's exchange rates."""
        return ""

    def tool_zz_logs(path: str) -> str:
        """Rotate and compress an application log file on disk."""
        return ""

    probes = ("zz_currency", "zz_logs")
    names = lambda schemas: [s["function"]["name"] for s in schemas]
    try:
        register(tool_zz_currency)
        register(tool_zz_logs)
        got = names(retrieve_tools("convert euros to dollars using exchange rates", k=1))
        assert "zz_currency" in got, f"❌ TODO 5: the closest tool is missing (got {got})."
        assert "zz_logs" not in got, "❌ TODO 5: return only the k closest tools plus the always-on ones."
        always_on.update(probes)
        got = names(retrieve_tools("convert euros to dollars using exchange rates", k=1))
        assert "zz_logs" in got, "❌ TODO 5: always-on tools must be added to the k closest."
        assert len(got) == len(set(got)), "❌ TODO 5: list each tool once."
    finally:
        always_on.difference_update(probes)
        for name in probes:
            tools.pop(name, None)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM toolbox WHERE name IN (:a, :b)", a=probes[0], b=probes[1])
        conn.commit()
    print("✅ TODO 5 passed: retrieve_tools returns the closest tools plus the always-on ones.")


def check_skill_search(conn, embed_model, tool_list_skills):
    """Checkpoint for TODO 7: the tool returns ranked skills, the same order the manifest uses."""
    query = "discover the schema of an Oracle database"
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM skillbox")
        count = cur.fetchone()[0]
    assert count, "❌ TODO 7: the skillbox is empty; seed it before this check."
    hits = json.loads(tool_list_skills(query, k=3))
    assert isinstance(hits, list) and len(hits) == min(3, count), "❌ TODO 7: return a JSON array of k skills."
    assert {"name", "category", "description"} <= set(hits[0]), "❌ TODO 7: each hit needs name, category, description."
    assert len(json.loads(tool_list_skills(query, k=1))) == 1, "❌ TODO 7: honour k."
    first = skill_manifest(conn, embed_model, query, k=3).splitlines()[1]
    assert first.startswith(f"  - {hits[0]['name']} "), "❌ TODO 7: order skills by cosine distance, best first."
    print("✅ TODO 7 passed: tool_list_skills returns ranked skills.")


def check_run_sql(TOOLS, tool_run_sql):
    """Hard-stop checkpoint for TODO 6: tool_run_sql is registered, read-only and returns JSON."""
    assert "run_sql" in TOOLS, "❌ TODO 6: keep the @register decorator."
    out = json.loads(tool_run_sql("SELECT level AS n FROM dual CONNECT BY level <= 5", max_rows=2))
    assert out.get("columns") == ["N"] and out.get("row_count") == 2, \
        f"❌ TODO 6: run the SQL and return wt.rows_json(cur, max_rows) (columns + at most max_rows rows), got {out}."
    assert json.loads(tool_run_sql("WITH t AS (SELECT 1 AS x FROM dual) SELECT x FROM t")).get("row_count") == 1, \
        "❌ TODO 6: WITH statements must run."
    assert "error" in json.loads(tool_run_sql("DROP TABLE x")), "❌ TODO 6: the read-only guard let a DROP through."
    assert "error" in json.loads(tool_run_sql("SELECT * FROM no_such_table_xyz")), \
        "❌ TODO 6: a database error must come back as {\"error\": ...}."
    print("✅ TODO 6 passed: tool_run_sql is registered, read-only and returns JSON.")
