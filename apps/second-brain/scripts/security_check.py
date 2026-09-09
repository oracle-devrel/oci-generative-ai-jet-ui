"""Routine security check — the repo and the brain audit themselves.

One deterministic pass, three surfaces, a report you actually read (rule 5):

  REPO   tracked files scanned for credential shapes (the shared redaction list,
         used here as a detector), gitignore guards verified present, no
         sensitive path tracked, the .env-write hook present AND behaving
         (block/allow matrix executed for real), deploy pins still exact.
  DB     read-only: untagged visibility rows (they'd count as public),
         credential shapes across chunks/captions/agent memory (counts only —
         values are never printed), and agent-written notes re-checked against
         the privacy deny-list.
  LIVE   optional: if SECURITY_CHECK_URL is set (your hosted MCP base URL),
         confirm /health answers and the API fails closed (401) without a token.

Exit code: 1 if anything RED, else 0 — so a scheduler can alert on failure.
Schedule it like every other loop (deterministic cron/launchd, rule 6), e.g.
weekly next to your sync. No LLM calls, no writes, no network beyond the
optional live probe.

Run from repo root:  ./.venv/bin/python scripts/security_check.py
"""
import datetime
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "oracle" / "agent"))
from redaction import SECRET_PATTERNS  # noqa: E402

# files that legitimately CONTAIN the patterns (scanners/scrubbers + their tests)
PATTERN_HOLDERS = {"scripts/redaction.py", "scripts/review.py", "scripts/security_check.py",
                   "tests/test_security_check.py"}
TEXT_SUFFIXES = {".py", ".md", ".txt", ".json", ".sql", ".sh", ".yml", ".yaml", ".toml",
                 ".html", ".js", ".css", ".webmanifest", ".example", ".gitignore",
                 ".dockerignore", ""}
REQUIRED_IGNORES = ["*.env", "private/", "sources/*/", "exports/", "cwallet.sso",
                    "tnsnames.ora", "*-wallet/"]
SENSITIVE_TRACKED = (".env", "cwallet.sso", "ewallet.p12", "tnsnames.ora", "sqlnet.ora")


def _git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          text=True, check=True).stdout


def check_tracked_secrets(findings):
    files = [f for f in _git("ls-files").splitlines()
             if f not in PATTERN_HOLDERS and pathlib.Path(f).suffix.lower() in TEXT_SUFFIXES]
    hits = 0
    for f in files:
        try:
            text = (ROOT / f).read_text(errors="ignore")
        except OSError:
            continue
        for pat in SECRET_PATTERNS:
            m = pat.search(text)
            if m:
                v = m.group(0)
                findings.append(("RED", f"tracked file {f}: credential-shaped text "
                                        f"({v[:6]}…, {len(v)} chars) — investigate, rotate, "
                                        f"and consider a history rewrite if it was real"))
                hits += 1
    if not hits:
        findings.append(("OK", f"tracked files: no credential shapes in {len(files)} text files"))


def check_ignore_guards(findings):
    ignore = (ROOT / ".gitignore").read_text()
    missing = [p for p in REQUIRED_IGNORES if p not in ignore]
    if missing:
        findings.append(("RED", f".gitignore lost required guard(s): {missing}"))
    else:
        findings.append(("OK", ".gitignore: all sensitive-path guards present"))
    bad = [f for f in _git("ls-files").splitlines()
           if f.endswith(SENSITIVE_TRACKED) and not f.endswith(".env.example")]
    bad += [f for f in _git("ls-files").splitlines() if f.startswith("private/")]
    if bad:
        findings.append(("RED", f"sensitive paths are TRACKED: {bad[:5]}"))
    else:
        findings.append(("OK", "no sensitive path is tracked (env/wallet/private)"))


def check_hook(findings):
    settings = ROOT / ".claude" / "settings.json"
    if not settings.exists():
        # some distributions can't ship dotfiles — absent is a setup nudge, not an alarm
        findings.append(("SKIP", ".claude/settings.json not present — create the "
                                 "env-guard hook (see AGENTS.md, Enforcement)"))
        return
    try:
        cfg = json.loads(settings.read_text())
        cmd = cfg["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    except (OSError, KeyError, json.JSONDecodeError):
        findings.append(("RED", ".claude/settings.json: the .env-write guard hook is gone"))
        return
    matrix = {"oracle/.env": 2, ".env.local": 2, "foo.env": 2,
              "oracle/.env.example": 0, "scripts/loader.py": 0}
    for path, want in matrix.items():
        r = subprocess.run(["sh", "-c", cmd], input=json.dumps(
            {"tool_input": {"file_path": path}}), capture_output=True, text=True)
        if r.returncode != want:
            findings.append(("RED", f"env-guard hook: {path} exited {r.returncode}, "
                                    f"expected {want} — the guard regressed"))
            return
    findings.append(("OK", "env-guard hook present and passing its block/allow matrix"))


def check_pins(findings):
    loose = []
    for line in (ROOT / "deploy" / "requirements.txt").read_text().splitlines():
        line = line.split("#")[0].strip()
        if line and "==" not in line:
            loose.append(line)
    if loose:
        findings.append(("RED", f"deploy/requirements.txt has UNPINNED deps: {loose} "
                                f"(the auth allowlist wraps library internals — pin exactly)"))
    else:
        findings.append(("OK", "deploy/requirements.txt: every dependency pinned exactly"))


def check_db(findings):
    try:
        import db
        conn = db.connect()
    except Exception as e:                                   # no DB is a skip, not a failure
        findings.append(("SKIP", f"database checks skipped ({type(e).__name__})"))
        return
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM posts WHERE visibility IS NULL")
        untagged = cur.fetchone()[0]
        findings.append(("RED" if untagged else "OK",
                         f"untagged posts (would ship as public): {untagged}"
                         + (" — run scripts/classify_private.py --apply" if untagged else "")))
        hits = {}
        for label, sql in [
                ("chunks", "SELECT p.platform_id, c.chunk FROM content_chunks c "
                           "JOIN posts p ON p.post_id=c.post_id"),
                ("captions", "SELECT platform_id, caption FROM posts"),
                ("agent_memory", "SELECT 'memory', task FROM agent_memory")]:
            cur.execute(sql)
            while True:
                rows = cur.fetchmany(500)
                if not rows:
                    break
                for key, text in rows:
                    if text and any(p.search(text) for p in SECRET_PATTERNS):
                        hits[f"{label}:{key}"] = hits.get(f"{label}:{key}", 0) + 1
        findings.append(("RED" if hits else "OK",
                         f"credential shapes in the brain: {hits or 'none'}"
                         + (" — scripts/review.py shows masked detail" if hits else "")))
        from oamp_memory import violates_privacy
        # triage knobs: SECURITY_CHECK_NOTE_ALLOW = comma-separated title prefixes for
        # recurring generated reports whose deny hits are reviewed-benign (they get new
        # ids every run); SECURITY_CHECK_ACK_IDS = one-off post ids reviewed and accepted
        allow = [p.strip() for p in
                 os.environ.get("SECURITY_CHECK_NOTE_ALLOW", "").split(",") if p.strip()]
        acked = {int(i) for i in
                 os.environ.get("SECURITY_CHECK_ACK_IDS", "").split(",") if i.strip().isdigit()}
        cur.execute("SELECT post_id, title, caption FROM posts WHERE platform_id='note' "
                    "AND NVL(visibility,'content')='content'")
        leaked = [f"[{pid}] {t[:60]}" for pid, t, c in cur.fetchall()
                  if pid not in acked
                  and not any(t.startswith(p) for p in allow)
                  and violates_privacy(f"{t}\n{c or ''}")]
        findings.append(("RED" if leaked else "OK",
                         f"agent notes vs privacy deny-list: {leaked or 'all clean'}"))
    finally:
        conn.close()


def check_live(findings):
    base = os.environ.get("SECURITY_CHECK_URL", "").rstrip("/")
    if not base:
        findings.append(("SKIP", "live probe skipped (set SECURITY_CHECK_URL to enable)"))
        return
    import urllib.error
    import urllib.request
    try:
        with urllib.request.urlopen(f"{base}/health", timeout=15) as r:
            findings.append(("OK" if r.status == 200 else "RED", f"/health -> {r.status}"))
    except (urllib.error.URLError, OSError) as e:
        findings.append(("RED", f"/health unreachable: {e}"))
        return
    try:
        with urllib.request.urlopen(f"{base}/api/ping", timeout=15) as r:
            findings.append(("RED", f"/api/ping answered {r.status} WITHOUT a token — "
                                    f"the UI is publicly readable"))
    except urllib.error.HTTPError as e:
        findings.append(("OK" if e.code in (401, 403, 404) else "RED",
                         f"/api/ping without token -> {e.code} (fails closed)"))
    except (urllib.error.URLError, OSError) as e:
        findings.append(("SKIP", f"/api/ping probe failed: {e}"))


def main():
    findings = []
    for check in (check_tracked_secrets, check_ignore_guards, check_hook,
                  check_pins, check_db, check_live):
        try:
            check(findings)
        except Exception as e:                               # a broken check must be visible
            findings.append(("RED", f"{check.__name__} crashed: {type(e).__name__}: {e}"))
    today = datetime.date.today().isoformat()
    lines = [f"# Security check — {today}", ""]
    worst = "OK"
    for level, msg in findings:
        mark = {"OK": "✓", "RED": "✗", "SKIP": "·"}[level]
        lines.append(f"- {mark} **{level}** {msg}")
        if level == "RED":
            worst = "RED"
        print(f"{mark} [{level}] {msg}")
    report_dir = ROOT / "private" / "reports" / "security"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / f"{today}.md").write_text("\n".join(lines) + "\n")
    print(f"\n{'ALL CLEAR' if worst == 'OK' else 'ATTENTION NEEDED'} — report saved to "
          f"private/reports/security/{today}.md")
    sys.exit(1 if worst == "RED" else 0)


if __name__ == "__main__":
    main()
