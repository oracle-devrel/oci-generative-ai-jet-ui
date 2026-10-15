"""The only tool-facing entry point. Identity is supplied by the trusted host."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime

from jsonschema import validate

from assembly import assemble, live, ref, scope_rank
from config import AS_OF, SCOPE, digest, dumps, row


class MemoryManager:
    def __init__(self, store, scope=None):
        self.store = store
        self.scope = deepcopy(scope or SCOPE)
        self.handles = {}
        self.manifest_hash = None

    def write_guideline(self, *, guideline_key, guideline_value, written_by, source_event_id):
        """Trusted host operation; not an MCP tool. Version a tenant guideline atomically."""
        import uuid
        from datetime import datetime
        from config import dumps
        with self.store.connection(self.scope) as conn,conn.cursor() as cur:
            cur.execute("SELECT id,version FROM guideline_memory WHERE guideline_key=:k AND user_id IS NULL AND agent_id IS NULL AND thread_id IS NULL AND valid_until IS NULL AND deleted_at IS NULL FOR UPDATE",k=guideline_key)
            previous=cur.fetchall();version=max([int(v) for _,v in previous],default=0)+1
            now=datetime.utcnow();id='context_'+uuid.uuid4().hex
            for old,_ in previous:cur.execute('UPDATE guideline_memory SET valid_until=:at WHERE id=:id',at=now,id=old)
            cur.execute("INSERT INTO guideline_memory(id,tenant_id,guideline_key,guideline_value,version,valid_from,written_by,source_event_id,created_at) VALUES(:id,:t,:k,JSON(:v),:ver,:at,:writer,:ev,:at)",id=id,t=self.scope['tenant_id'],k=guideline_key,v=dumps(guideline_value),ver=version,at=now,writer=written_by,ev=source_event_id)
            conn.commit()
            return ['guideline',id,version]

    def active_toolbox(self):
        return [
            r
            for r in self.store.toolbox_rows(self.scope)
            if r["kind"] == "tool"
            and live(r, datetime.utcnow())
            and self.scope["agent_id"] in r["meta"]["allowed_agents"]
        ]

    def authorize(self, name, arguments):
        allowed = {"search_memory", "lookup_entity", "expand", "clarify"}
        entry = next((r for r in self.active_toolbox() if r["meta"]["name"] == name), None)
        if entry is None or name not in allowed:
            raise PermissionError("Tool is unavailable in this scope.")
        validate(arguments, entry["meta"]["inputSchema"])
        return entry

    def issue_window(self, window):
        if window["manifest"]["scope"] != self.scope:
            raise PermissionError("Window belongs to a different scope.")
        self.manifest_hash = window["manifest"]["request_hash"]
        self.handles = {b["id"]: b["ref"] for b in window["memories"]}

    def load_compressions(self, requested):
        """Resolve requested compressions to their stored, scoped versions; never trust the caller's copy."""
        stored = {tuple(ref(r)): r for r in self.store.compression_rows(self.scope)}
        loaded = {}
        for source_ref, comp in (requested or {}).items():
            item = stored.get(tuple(ref(comp)))
            if item is None:
                raise PermissionError("Compression is not stored in this scope.")
            loaded[tuple(source_ref)] = item
        return loaded

    def build_window(self, compressions=None, **kwargs):
        question=kwargs.pop("question",None)
        from config import QUESTION
        from retrieval import understand_query
        plan=understand_query(question or QUESTION)
        kwargs.setdefault('intent','comparison' if plan['intent']=='comparison' else 'fact_check')
        scn, rows = self.store.snapshot(self.scope,question or QUESTION)
        result = assemble(
            rows,
            self.scope,
            scn=scn,
            mode=self.store.mode,
            compressions=self.load_compressions(compressions),
            **kwargs,
        )
        result["manifest"]["question_ref"] = ref(next(r for r in rows if r["slice"]=="question"))
        byref={tuple(ref(r)):r for r in rows}
        deps=result["manifest"]["dependencies"]
        for d in deps:
            source=byref.get(tuple(d))
            if source:
                for x in source["meta"].get("source_refs",[]):
                    if x not in deps:deps.append(x)
        for b in result["memories"]:
            if b["compression_ref"] and b["compression_ref"] not in deps:deps.append(b["compression_ref"])
        result["manifest_event_id"]=self.store.save_manifest(result["manifest"], self.scope)
        self.issue_window(result)
        return result

    def invoke(self, name, arguments):
        self.authorize(name, arguments)
        call_event=self.store.save_event("tool_call", {"name": name, "arguments": arguments}, self.scope)
        rows = self.store.current_rows(self.scope)
        if name == "lookup_entity":
            hits = [
                r
                for r in rows
                if r["kind"] == "entity"
                and live(r, datetime.utcnow())
                and r["meta"].get("subject") == arguments["subject"]
                and r["meta"].get("predicate") == arguments["predicate"]
            ]
            hits.sort(key=lambda r: (scope_rank(r), r["version"], r["id"]), reverse=True)
            if hits:
                current = hits[0]
                history = [
                    r
                    for r in rows
                    if r["kind"] == "entity"
                    and r["claim_key"] == current["claim_key"]
                    and r["deleted_at"] is None
                    and r["valid_from"] <= datetime.utcnow()
                    and ref(r) != ref(current)
                ]
                result = {
                    "status": "found",
                    "items": [public_item(current)],
                    "history": [
                        {"ref": ref(r), "content": r["content"], "status": "historical"}
                        for r in history
                    ],
                }
            else:
                result = {"status": "not_found", "items": []}
        elif name == "expand":
            reference = self.handles.get(arguments["memory_id"])
            match = next((r for r in rows if ref(r) == reference and live(r, datetime.utcnow())), None)
            if match is None:
                raise PermissionError("Pointer is unavailable or no longer authorized.")
            result = {
                "status": "found",
                "items": [public_item(match)],
                "window_hash": self.manifest_hash,
            }
        elif name == "search_memory":
            hits=self.store.hybrid(self.scope,arguments["query"],evaluation_time=datetime.utcnow())
            fresh=self.store.snapshot(self.scope,arguments["query"])[1]
            byid={r["id"]:r for r in fresh if r["kind"]=="kb"}
            # Two results keep the tool reserve bounded; callers can narrow the query.
            result={"status":"found","retrieval":"vector+OracleText+RRF+BGE_RERANKER","items":[public_item(byid[h["id"]]) for h in hits[:2] if h["id"] in byid]}

        else:
            result = {"status": "needs_user", "question": arguments["question"], "items": []}
        result_event=self.store.save_event("tool_result", result, self.scope)
        result["event_refs"]=[["conversation",call_event,None],["conversation",result_event,None]]
        return result


def public_item(item):
    return {
        key: deepcopy(item[key])
        for key in ("kind", "id", "version", "content", "source_event_id", "meta", "tenant_id", "user_id", "agent_id", "thread_id", "content_hash")
    } | {"slice": "tool_results", "annotation_refs": []}


def compression_for(source, text=None, model=None):
    """Stored compression names its source bytes and actual generating model."""
    if not text or not model:raise ValueError("Compression requires text and a generating model identifier.")
    origin="model"
    ancestors=source['meta'].get('source_refs',[])+([source['meta']['parent_ref']] if source['meta'].get('parent_ref') else [])
    ancestors=list({dumps(x):x for x in ancestors}.values())
    key = digest(dumps([ref(source),ancestors,text,model]))[:30]
    return row(
        "compression",
        "compression-" + key,
        text,
        tenant_id=source["tenant_id"],
        user_id=source["user_id"],
        agent_id=source["agent_id"],
        thread_id=source["thread_id"],
        meta={
            "source_refs": [ref(source)],
            "source_hash": source["content_hash"],
            "source_ancestors": ancestors,
            "origin": origin,
            "model": model,
            "prompt_version": "compression-1",
        },
    )


def serialize_result(result):
    return json.dumps(result, sort_keys=True)
