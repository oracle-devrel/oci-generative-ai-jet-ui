"""Auto-detect everything built on the brain and emit the registry the web UI reads.

Nobody hand-maintains a list. This scans the codebase and writes:
  web/registry.json                      — the GENERIC catalog (public paths)
  private/server/registry.private.json   — PRIVATE items (private/ + .claude/), only if present

The registry only changes when you add/remove an agent/tool/job — a code change, which
redeploys anyway — so regenerating here (and in the daily sync) keeps it current for free.

Run:  ./.venv/bin/python scripts/build_registry.py
"""
import ast
import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _tracked():
    """Repo-relative paths git actually tracks. The GENERIC registry is committed to the
    public repo, so it must be built from tracked files ONLY — an untracked personal
    script dropped into scripts/ or oracle/agent/ must never get its name + docstring
    auto-committed by the pre-commit hook. Returns None if git is unavailable (then the
    caller keeps everything, matching the old behavior outside a checkout)."""
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "ls-files"],
                             capture_output=True, text=True, check=True, timeout=10)
        return set(out.stdout.splitlines())
    except Exception:
        return None


def _is_tracked(p, tracked):
    return tracked is None or _rel(p) in tracked


def _title(stem):
    return re.sub(r"[_\-]+", " ", stem).strip().capitalize()


def _rel(p):
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return p.name


def _clean(desc):
    """First sentence-ish, em dashes normalized (the UI copy avoids them)."""
    d = (desc or "").strip().splitlines()[0].strip() if desc else ""
    return d.replace(" — ", ": ").replace("—", ", ").strip()


def _module_doc(path):
    try:
        return _clean(ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))))
    except Exception:
        return ""


def _dec_description(dec):
    """A `description=...` keyword arg on a decorator Call, if it's a plain string literal."""
    if isinstance(dec, ast.Call):
        for kw in dec.keywords:
            if kw.arg == "description" and isinstance(kw.value, ast.Constant):
                return str(kw.value.value)
    return ""


def _decorated(path, attrs):
    """Functions in `path` decorated with @<obj>.<attr> for attr in attrs (e.g. tool/prompt).
    Walks the whole tree so tools registered inside a register() function are found too.
    Description = the function docstring, else the decorator's description= (playbooks use that)."""
    out = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except Exception:
        return out
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            d = dec.func if isinstance(dec, ast.Call) else dec
            if isinstance(d, ast.Attribute) and d.attr in attrs:
                desc = _clean(ast.get_docstring(node)) or _clean(_dec_description(dec))
                out.append({"name": node.name, "attr": d.attr, "desc": desc})
    return out


def _skill(md):
    """Parse a SKILL.md YAML frontmatter for name + description."""
    txt = md.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---", txt, re.S)
    fm = m.group(1) if m else ""
    def field(k):
        mm = re.search(rf"^{k}:\s*(.+)$", fm, re.M)
        return mm.group(1).strip().strip("'\"") if mm else ""
    return field("name") or md.parent.name, field("description")


def _plist(p):
    txt = p.read_text(encoding="utf-8", errors="ignore")
    label = (re.search(r"<key>Label</key>\s*<string>([^<]+)</string>", txt) or [None, p.stem])[1]
    if re.search(r"<key>StartInterval</key>\s*<integer>3600", txt):
        when = "hourly"
    elif re.search(r"<key>StartCalendarInterval</key>", txt):
        when = "weekly"
    else:
        when = "scheduled"
    return label, when


def _cat(cats, key, label, desc=""):
    for c in cats:
        if c["key"] == key:
            return c
    c = {"key": key, "label": label, "desc": desc, "items": []}
    cats.append(c)
    return c


AGENT_SKIP = {"agent"}  # agent.py is the demo, kept but flagged; skip scaffolding below
SKIP_PREFIX = ("_", "legacy_", "demo_", "test_")


def _agent_files(folder):
    if not folder.is_dir():
        return []
    files = list(folder.glob("*_agent.py"))
    if (folder / "agent.py").exists():
        files.append(folder / "agent.py")
    return sorted(f for f in files if not f.name.startswith(SKIP_PREFIX))


def _scripts_split():
    """Split scripts/*.py into (sources=loaders that write posts, jobs=runnable brain scripts)."""
    sources, jobs = [], []
    for p in sorted((ROOT / "scripts").glob("*.py")):
        if p.name.startswith(SKIP_PREFIX) or p.name == "build_registry.py":
            continue
        txt = p.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"into\s+posts", txt, re.I):
            sources.append(p)
        elif "__main__" in txt and re.search(r"\bimport\s+(db|content|wiki|memory|semantic_memory)\b", txt):
            jobs.append(p)
    return sources, jobs


def build_generic():
    tracked = _tracked()   # public registry = tracked files only (see _tracked docstring)
    cats = []
    ag = _cat(cats, "agents", "Agents", "Reasoning agents grounded in your content + memory.")
    for f in _agent_files(ROOT / "oracle" / "agent"):
        if not _is_tracked(f, tracked):
            continue
        ag["items"].append({"name": _title(f.stem), "desc": _module_doc(f), "where": _rel(f), "scope": "generic"})
    # tools + playbooks from the public MCP server
    tl = _cat(cats, "tools", "Tools", "The MCP tools that reach the brain from any AI client.")
    pb = _cat(cats, "playbooks", "Playbooks", "Prompt recipes any MCP client runs with the read tools.")
    for d in _decorated(ROOT / "oracle" / "agent" / "mcp_server.py", {"tool", "prompt"}):
        bucket = tl if d["attr"] == "tool" else pb
        bucket["items"].append({"name": d["name"], "desc": d["desc"], "where": "mcp_server.py", "scope": "generic"})
    src, jobs = _scripts_split()
    so = _cat(cats, "sources", "Sources", "Loaders that pull your content in (official APIs and your exports).")
    for f in src:
        if not _is_tracked(f, tracked):
            continue
        so["items"].append({"name": _title(f.stem), "desc": _module_doc(f), "where": _rel(f), "scope": "generic"})
    jb = _cat(cats, "jobs", "Jobs & loops", "Background automation that keeps the brain fed and fresh.")
    for f in jobs:
        if not _is_tracked(f, tracked):
            continue
        jb["items"].append({"name": _title(f.stem), "desc": _module_doc(f), "where": _rel(f), "scope": "generic"})
    ig = _cat(cats, "integrations", "Integrations", "How the brain reaches the outside world.")
    for fname, label in [("mcp_http.py", "Hosted MCP server"), ("webui.py", "Web memory UI"),
                         ("telegram_api.py", "Telegram idea-capture"), ("slack_api.py", "Slack brain-dump")]:
        p = ROOT / "oracle" / "agent" / fname
        if p.exists() and _is_tracked(p, tracked):
            ig["items"].append({"name": label, "desc": _module_doc(p), "where": _rel(p), "scope": "generic"})
    return [c for c in cats if c["items"]]


def build_private():
    if not (ROOT / "private").is_dir():
        return []
    cats = []
    ag = _cat(cats, "agents", "Agents")
    for f in sorted((ROOT / "private" / "agents").glob("*.py")) if (ROOT / "private" / "agents").is_dir() else []:
        if f.name.startswith(SKIP_PREFIX):
            continue
        ag["items"].append({"name": _title(f.stem), "desc": _module_doc(f), "where": _rel(f), "scope": "private"})
    ext = ROOT / "private" / "server" / "server_ext.py"
    if ext.exists():
        tl = _cat(cats, "tools", "Tools")
        pb = _cat(cats, "playbooks", "Playbooks")
        for d in _decorated(ext, {"tool", "prompt"}):
            (tl if d["attr"] == "tool" else pb)["items"].append(
                {"name": d["name"], "desc": d["desc"], "where": _rel(ext), "scope": "private"})
    hx = ROOT / "private" / "server" / "http_ext.py"
    if hx.exists():
        _cat(cats, "integrations", "Integrations")["items"].append(
            {"name": "MCP Apps diagram panel", "desc": _module_doc(hx), "where": _rel(hx), "scope": "private"})
    sk = _cat(cats, "skills", "Skills", "Claude Code skills you authored.")
    mds = []
    for basedir in (ROOT / "private" / "skills", ROOT / "private" / "claude-code" / "skills",
                    ROOT / ".claude" / "skills"):
        if basedir.is_dir():
            mds += list(basedir.glob("*/SKILL.md"))
    seen = set()
    for md in sorted(mds):
        if "worktrees" in str(md) or md.parent.name in seen:
            continue
        seen.add(md.parent.name)
        name, desc = _skill(md)
        sk["items"].append({"name": name, "desc": _clean(desc), "where": _rel(md.parent), "scope": "private"})
    sc = _cat(cats, "scheduled", "Scheduled", "Recurring jobs on your machine (launchd).")
    for pl in sorted((ROOT / "private").glob("**/*.plist")):
        label, when = _plist(pl)
        sc["items"].append({"name": label.split(".")[-1].title() if "." in label else label,
                            "desc": when.capitalize() + " job.", "where": _rel(pl), "scope": "private"})
    return [c for c in cats if c["items"]]


def main():
    generic = build_generic()
    (ROOT / "web" / "registry.json").write_text(
        json.dumps({"categories": generic}, indent=2) + "\n", encoding="utf-8")
    n = sum(len(c["items"]) for c in generic)
    print(f"web/registry.json: {n} generic items across {len(generic)} categories")
    private = build_private()
    if private:
        out = ROOT / "private" / "server" / "registry.private.json"
        out.write_text(json.dumps({"categories": private}, indent=2) + "\n", encoding="utf-8")
        m = sum(len(c["items"]) for c in private)
        print(f"private/server/registry.private.json: {m} private items across {len(private)} categories")


if __name__ == "__main__":
    main()
