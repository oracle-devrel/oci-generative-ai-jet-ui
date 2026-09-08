#!/bin/bash

echo "============================================"
echo "  From RAG to Agents Workshop - Starting"
echo "============================================"

# --- Guard: ensure oracledb is installed regardless of prebuild state ---
python3 -c "import oracledb" > /dev/null 2>&1 || {
  echo ""
  echo "[0/3] oracledb not found — installing now..."
  pip install -q oracledb
}

# --- Step 1: Wait for Docker daemon ---
echo ""
echo "[1/3] Waiting for Docker daemon..."
for i in $(seq 1 15); do
  docker info > /dev/null 2>&1 && echo "  Docker is ready." && break \
    || { [ $i -lt 15 ] && echo "  Waiting for Docker... (attempt $i/15)" && sleep 3; }
done

# --- Step 2: Start Oracle container ---
echo ""
echo "[2/3] Starting Oracle AI Database..."
echo "  Removing previous oracle-free container (if present)..."
docker rm -f oracle-free > /dev/null 2>&1 || true
docker compose -f .devcontainer/docker-compose.yml up -d oracle 2>/dev/null
echo "  Container started."

# --- Step 3: Wait for Oracle to be ready, normalize passwords, then configure vector memory ---
echo ""
echo "[3/3] Waiting for Oracle to accept connections..."
ORACLE_UP=0
for i in $(seq 1 20); do
  docker exec oracle-free healthcheck.sh > /dev/null 2>&1
  if [ $? -eq 0 ]; then
    echo "  Oracle is accepting connections."
    ORACLE_UP=1
    break
  else
    echo "  Attempt $i/20 — waiting 10s..."
    sleep 10
  fi
done

if [ $ORACLE_UP -eq 0 ]; then
  echo "  ERROR: Oracle did not start. Run: docker logs oracle-free"
  exit 1
fi

# Existing volumes may keep old credentials; normalize to workshop defaults.
echo "  Resetting database passwords to workshop defaults..."
docker exec oracle-free resetPassword OraclePwd_2025 > /dev/null 2>&1
if [ $? -ne 0 ]; then
  echo "  ERROR: Could not reset database password inside oracle-free."
  exit 1
fi

# Set vector_memory_size in both CDB root and FREEPDB1 using SPFILE fallback sizes.
echo "  Setting vector_memory_size in CDB and PDB (SPFILE fallback)..."
python3 << 'PYEOF'
import oracledb, sys

try:
    conn = oracledb.connect(
        user="sys",
        password="OraclePwd_2025",
        dsn="localhost:1521/FREE",
        mode=oracledb.SYSDBA
    )
    cur = conn.cursor()
    selected_mb = None
    last_err = None
    for mb in (1024, 768, 512, 384, 256, 128):
        try:
            cur.execute("ALTER SESSION SET CONTAINER = CDB$ROOT")
            cur.execute(f"ALTER SYSTEM SET vector_memory_size = {mb}M SCOPE=SPFILE")
            cur.execute("ALTER SESSION SET CONTAINER = FREEPDB1")
            cur.execute(f"ALTER SYSTEM SET vector_memory_size = {mb}M SCOPE=SPFILE")
            selected_mb = mb
            break
        except Exception as e:
            last_err = e
            continue
    if selected_mb is None:
        raise RuntimeError(f"Unable to set vector_memory_size to any supported value: {last_err}")
    # Ensure workshop user exists and has expected password/privileges in FREEPDB1.
    try:
        cur.execute("ALTER USER VECTOR IDENTIFIED BY VectorPwd_2025 ACCOUNT UNLOCK")
    except Exception:
        cur.execute("CREATE USER VECTOR IDENTIFIED BY VectorPwd_2025")
    cur.execute("GRANT CONNECT, RESOURCE TO VECTOR")
    cur.execute("GRANT UNLIMITED TABLESPACE TO VECTOR")
    try:
        cur.execute("GRANT CREATE PROPERTY GRAPH TO VECTOR")
    except Exception:
        pass
    try:
        cur.execute("GRANT READ ANY PROPERTY GRAPH TO VECTOR")
    except Exception:
        pass
    conn.commit()
    conn.close()
    print(f"  vector_memory_size applied: {selected_mb}M in CDB$ROOT and FREEPDB1.")
    print("  VECTOR user ensured in FREEPDB1.")
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)
PYEOF

if [ $? -ne 0 ]; then
  echo "  ERROR: Failed to set vector_memory_size."
  exit 1
fi

echo "  Restarting Oracle to apply SPFILE change..."
docker restart oracle-free

# Wait for Oracle to come back with vector_memory_size active in both containers
ORACLE_READY=0
for i in $(seq 1 20); do
  python3 -c "
import oracledb, sys
try:
    conn = oracledb.connect(
        user='sys',
        password='OraclePwd_2025',
        dsn='localhost:1521/FREE',
        mode=oracledb.SYSDBA
    )
    cur = conn.cursor()
    values = {}
    for container in ('CDB\$ROOT', 'FREEPDB1'):
        cur.execute(f'ALTER SESSION SET CONTAINER = {container}')
        cur.execute(\"SELECT value FROM v\\\$parameter WHERE name = 'vector_memory_size'\")
        row = cur.fetchone()
        values[container] = int(row[0]) if row and row[0] else 0
    conn.close()
    if values['CDB\$ROOT'] > 0 and values['FREEPDB1'] > 0:
        root_mb = values['CDB\$ROOT'] // (1024**2)
        pdb_mb = values['FREEPDB1'] // (1024**2)
        print(f'  vector_memory_size confirmed: CDB\$ROOT={root_mb}M FREEPDB1={pdb_mb}M')
        sys.exit(0)
    else:
        root_mb = values['CDB\$ROOT'] // (1024**2)
        pdb_mb = values['FREEPDB1'] // (1024**2)
        print(f'  vector_memory_size current values: CDB\$ROOT={root_mb}M FREEPDB1={pdb_mb}M')
        sys.exit(2)
except:
    sys.exit(1)
"
  RC=$?
  if [ $RC -eq 0 ]; then
    ORACLE_READY=1
    break
  elif [ $RC -eq 2 ]; then
    echo "  Oracle up but vector_memory_size still 0 — waiting 10s..."
    sleep 10
  else
    echo "  Attempt $i/20 — waiting 10s..."
    sleep 10
  fi
done

if [ $ORACLE_READY -eq 0 ]; then
  echo ""
  echo "  ERROR: vector_memory_size not confirmed in both CDB\$ROOT and FREEPDB1 after restart."
  echo "  Aborting to prevent ORA-51962 during notebook execution."
  exit 1
fi

# Verify workshop application user login used by notebooks.
python3 -c "
import oracledb, sys
try:
    conn = oracledb.connect(user='VECTOR', password='VectorPwd_2025', dsn='localhost:1521/FREEPDB1')
    conn.close()
    print('  VECTOR user login confirmed in FREEPDB1.')
    sys.exit(0)
except Exception as e:
    print(f'  ERROR: VECTOR login failed: {e}')
    sys.exit(1)
"
if [ $? -ne 0 ]; then
  echo "  Aborting because notebook user VECTOR is not ready."
  exit 1
fi

echo ""
echo "============================================"
echo "  Workshop is ready!"
echo ""
echo "  1. Open:   workshop/notebook_student.ipynb"
echo "  2. Kernel: From RAG to Agents Workshop"
echo "  3. Guides: docs/part-1-oracle-setup.md"
echo "============================================"
