"""Load the ONNX embedding model ('MINILM') into the database directly as a BLOB.

No Object Storage / PAR needed — reads the local .onnx and streams it to whatever db.connect()
points at (use for the cloud Autonomous DB). Idempotent: drops an existing MINILM first.

  python scripts/load_model_cloud.py
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "oracle" / "agent"))
import db          # noqa: E402
import oracledb    # noqa: E402

MODEL = ROOT / "oracle" / "models" / "all_MiniLM_L12_v2.onnx"
META = '{"function":"embedding","embeddingOutput":"embedding","input":{"input":["DATA"]}}'


def main():
    data = MODEL.read_bytes()
    print(f"model: {len(data)/1e6:.0f} MB — connecting")
    conn = db.connect()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN DBMS_VECTOR.DROP_ONNX_MODEL('MINILM', force => true); END;")
        print("dropped existing MINILM (if any)")
    except Exception as e:
        print("drop skipped:", str(e).split("\n")[0])

    print("uploading model as BLOB...")
    lob = conn.createlob(oracledb.DB_TYPE_BLOB)
    lob.write(data)
    cur.execute("BEGIN DBMS_VECTOR.LOAD_ONNX_MODEL(:n, :b, JSON(:m)); END;",
                n="MINILM", b=lob, m=META)
    conn.commit()
    print("model loaded — verifying embedding...")
    ok = cur.execute(
        "SELECT VECTOR_EMBEDDING(MINILM USING 'hello world' AS DATA) IS NOT NULL FROM dual"
    ).fetchone()[0]
    print("MINILM works:", bool(ok))
    conn.close()


if __name__ == "__main__":
    main()
