"""Drop-zip-and-forget: pick up new ChatGPT/Claude data-export zips and load them.

Chat platforms have no push API, so exports are the freshness path. This removes the
manual steps: request the export, and when the zip lands in your downloads folder,
the daily sync (or a manual run) finds it, identifies which platform it is, extracts
conversations.json, and runs the right loader.

  ./.venv/bin/python scripts/ingest_exports.py

Config: EXPORT_WATCH_DIR (default: ~/Downloads). State lives in exports/.ingest_watch.json
so each zip is processed once. Identification is by content, not filename: a ChatGPT
export's conversations.json items carry "mapping"; a Claude export's carry "chat_messages".
"""
import json
import os
import pathlib
import subprocess
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
WATCH = pathlib.Path(os.environ.get("EXPORT_WATCH_DIR", str(pathlib.Path.home() / "Downloads")))
STATE = ROOT / "exports" / ".ingest_watch.json"
PY = sys.executable


def _state():
    try:
        return json.load(open(STATE))
    except Exception:
        return {"processed": {}}


def _kind(zf, name):
    """Peek at conversations.json inside the zip: chatgpt or claude (or None)."""
    with zf.open(name) as f:
        head = f.read(4096).decode("utf-8", "ignore")
    if '"mapping"' in head:
        return "chatgpt"
    if '"chat_messages"' in head or '"uuid"' in head:
        return "claude"
    return None


def main():
    state = _state()
    done = state["processed"]
    found = []
    for z in sorted(WATCH.glob("*.zip")):
        key = f"{z.name}:{int(z.stat().st_mtime)}"
        if key in done:
            continue
        try:
            zf = zipfile.ZipFile(z)
        except Exception:
            continue
        convs = [n for n in zf.namelist() if n.endswith("conversations.json")]
        if not convs:
            done[key] = "no-conversations"
            continue
        kind = _kind(zf, convs[0])
        if not kind:
            done[key] = "unknown-format"
            continue

        stamp = key.split(":")[1]
        if kind == "chatgpt":
            dest = ROOT / "exports" / "chatgpt" / f"conversations-{stamp}.json"
        else:
            dest = ROOT / "exports" / "claude" / "conversations.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(convs[0]) as src:
            dest.write_bytes(src.read())
        print(f"found {kind} export: {z.name} -> {dest.relative_to(ROOT)}")
        found.append((kind, key))

    loaders = {"chatgpt": "chatgpt.py", "claude": "claude_chats.py"}
    for kind in {k for k, _ in found}:
        print(f"=== loading {kind} ===", flush=True)
        rc = subprocess.run([PY, str(ROOT / "scripts" / loaders[kind])]).returncode
        for k, key in found:
            if k == kind:
                done[key] = "loaded" if rc == 0 else "load-failed"
        if rc:
            print(f"  {kind} loader FAILED — zip will be retried next run")
            done.update({key: None for k, key in found if k == kind})
            for k, key in found:
                if k == kind:
                    done.pop(key, None)

    STATE.parent.mkdir(parents=True, exist_ok=True)
    json.dump(state, open(STATE, "w"), indent=1)
    if not found:
        print("no new chat exports found")


if __name__ == "__main__":
    main()
