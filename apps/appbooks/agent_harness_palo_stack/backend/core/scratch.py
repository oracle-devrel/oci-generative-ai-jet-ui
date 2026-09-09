"""The in-database scratch filesystem (SecureFile-LOB backed) + progressive-disclosure
file tools. Files are rows: durable, ACID, and they survive process death."""
from __future__ import annotations

import re

from backend.core import db

MOUNT = "/scratch"


def _abs(path: str) -> str:
    path = "/" + path.strip("/")
    return path if path.startswith(MOUNT) else MOUNT + path


def write(path: str, content) -> None:
    data = content.encode("utf-8") if isinstance(content, str) else content
    db.x(
        """MERGE INTO agent_scratch d USING (SELECT :p AS path FROM dual) s ON (d.path = s.path)
            WHEN MATCHED THEN UPDATE SET content=:c, is_dir='N', promoted='N', updated_at=SYSTIMESTAMP
            WHEN NOT MATCHED THEN INSERT (path, content) VALUES (:p, :c)""",
        {"p": _abs(path), "c": data},
    )


def read(path: str) -> str:
    r = db.q("SELECT content FROM agent_scratch WHERE path=:p", {"p": _abs(path)})
    if not r:
        raise FileNotFoundError(_abs(path))
    b = r[0]["CONTENT"]
    return b.decode("utf-8", errors="replace") if isinstance(b, bytes | bytearray) else (b or "")


def exists(path: str) -> bool:
    return bool(db.q("SELECT 1 FROM agent_scratch WHERE path=:p", {"p": _abs(path)}))


def listing(root: str = "/"):
    pre = _abs(root).rstrip("/") + "/%"
    return [
        r["PATH"]
        for r in db.q(
            "SELECT path, updated_at FROM agent_scratch WHERE path LIKE :pre AND is_dir='N' ORDER BY path",
            {"pre": pre},
        )
    ]


def tail(path: str, n: int = 10) -> str:
    return "\n".join(read(path).splitlines()[-n:])


def read_range(path: str, start: int, end: int) -> str:
    return "\n".join(read(path).splitlines()[max(0, start - 1) : end])


def grep(pattern: str, root: str = "/"):
    rx = re.compile(pattern, re.IGNORECASE)
    hits = []
    for p in listing(root):
        try:
            for i, line in enumerate(read(p).splitlines(), 1):
                if rx.search(line):
                    hits.append({"path": p, "line": i, "text": line.strip()[:200]})
        except Exception:
            continue
    return hits
