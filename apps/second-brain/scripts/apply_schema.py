"""Apply the schema files (oracle/schema/0*.sql) over a db.connect() connection.

Works for BOTH local and cloud (Autonomous via wallet) — db.connect() picks the target from
oracle/.env. Idempotent: "already exists" errors are tolerated, so it's safe to re-run.

  python scripts/apply_schema.py            # apply to whatever DB_* in oracle/.env points at
  python scripts/apply_schema.py --dry-run  # just print the parsed statements, don't execute

Used for the cloud migration: set the wallet env (DB_WALLET_DIR, DB_DSN, ...) and run this to
build the whole schema in Autonomous in one shot — no manual SQL pasting. (The ONNX model load
happens separately via scripts/load_model_cloud.py — direct BLOB, no Object Storage;
see docs/CLOUD_MIGRATION.md.)
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "oracle" / "agent"))
import db  # noqa: E402

SCHEMA_DIR = ROOT / "oracle" / "schema"
# tolerate "already exists / already granted / already seeded" so re-runs are idempotent
TOLERATE = ("ORA-00955", "ORA-01920", "ORA-00942", "ORA-01430", "ORA-02260", "ORA-01442",
            "ORA-00001")


def statements(sql_text):
    """Split a sqlplus-style schema file into executable statements (strip comments, split on ;).
    The schema files contain no PL/SQL blocks, so a ;-terminator split is safe."""
    out, buf = [], []
    for line in sql_text.splitlines():
        if "--" in line:                      # strip inline / full-line comments
            line = line[: line.index("--")]
        buf.append(line)
        if line.rstrip().endswith(";"):
            stmt = "\n".join(buf).strip().rstrip(";").strip()
            if stmt:
                out.append(stmt)
            buf = []
    tail = "\n".join(buf).strip().rstrip(";").strip()
    if tail:
        out.append(tail)
    return out


def main():
    dry = "--dry-run" in sys.argv
    files = sorted(SCHEMA_DIR.glob("0*.sql"))
    conn = None if dry else db.connect()
    ok = skipped = errors = 0
    for f in files:
        stmts = statements(f.read_text())
        print(f"\n== {f.name}  ({len(stmts)} statements) ==")
        for s in stmts:
            head = " ".join(s.split())[:72]
            # CURRENT_SCHEMA=CCC is a local-container convenience; on cloud we create in the
            # connected user's own schema, so skip it.
            if s.upper().startswith("ALTER SESSION SET CURRENT_SCHEMA"):
                print("   (skip CURRENT_SCHEMA — using connected user's schema)")
                continue
            if dry:
                print("   ", head)
                continue
            try:
                with conn.cursor() as cur:
                    cur.execute(s)
                ok += 1
                print("   ok:", head)
            except Exception as e:
                msg = str(e).split("\n")[0]
                if any(code in msg for code in TOLERATE):
                    skipped += 1
                    print("   skip(exists):", head)
                else:
                    errors += 1
                    print("   ERR:", msg, "::", head)
    if conn:
        conn.commit()
        conn.close()
        print(f"\ndone — {ok} applied, {skipped} skipped(exists), {errors} errors")
    else:
        print("\n(dry run — nothing executed)")


if __name__ == "__main__":
    main()
