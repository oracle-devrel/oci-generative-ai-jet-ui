#!/bin/bash
# Oracle AI Database 26ai Docker setup script

set -e

CONTAINER_NAME="oracle-ai-demo"
ORACLE_PWD="OraclePwd_2025"
IMAGE="container-registry.oracle.com/database/free:latest"

echo "=== Oracle AI Database Setup ==="

# Check if container already exists
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Container '${CONTAINER_NAME}' already exists."
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo "Container is already running."
    else
        echo "Starting existing container..."
        docker start ${CONTAINER_NAME}
    fi
else
    echo "Creating new Oracle container..."
    docker run -d \
        --name ${CONTAINER_NAME} \
        -p 1521:1521 -p 5500:5500 \
        -e ORACLE_PWD=${ORACLE_PWD} \
        -e ORACLE_SID=FREE \
        -e ORACLE_PDB=FREEPDB1 \
        -v oracle_ai_demo_data:/opt/oracle/oradata \
        ${IMAGE}
fi

echo ""
echo "Waiting for database to be ready (this may take 2-3 minutes)..."
echo ""

# Wait for database to be ready
for i in $(seq 1 60); do
    if docker exec ${CONTAINER_NAME} bash -c "echo 'SELECT 1 FROM DUAL;' | sqlplus -s / as sysdba 2>/dev/null | grep -q '1'" 2>/dev/null; then
        echo "Database is ready!"
        break
    fi
    printf "."
    sleep 5
done

echo ""

# Fix listener for ARM Macs
echo "Fixing listener configuration..."
docker exec ${CONTAINER_NAME} bash -lc '
    export ORACLE_HOME=${ORACLE_HOME:-/opt/oracle/product/26ai/dbhomeFree}
    export PATH=$ORACLE_HOME/bin:$PATH
    if [ -f "$ORACLE_HOME/network/admin/listener.ora" ]; then
        sed -i "s/(HOST *= *[^)]*)/(HOST = 0.0.0.0)/" "$ORACLE_HOME/network/admin/listener.ora"
        lsnrctl stop 2>/dev/null || true
        lsnrctl start
        echo "ALTER SYSTEM REGISTER;" | sqlplus -s / as sysdba
        echo "Listener fixed."
    else
        echo "Listener.ora not found at expected path, skipping."
    fi
' 2>/dev/null || echo "Warning: Could not fix listener (may not be needed)"

# Increase vector memory pool for HNSW indexes
echo "Configuring vector memory pool (requires DB restart)..."
docker exec ${CONTAINER_NAME} bash -c '
    sqlplus -s / as sysdba <<EOF
ALTER SYSTEM SET vector_memory_size=512M SCOPE=SPFILE;
SHUTDOWN IMMEDIATE;
STARTUP;
ALTER PLUGGABLE DATABASE ALL OPEN;
ALTER SYSTEM REGISTER;
EOF
' 2>/dev/null && echo "Vector memory set to 512M." || echo "Warning: Could not set vector memory (may need manual config)"

echo ""
echo "=== Setup complete ==="
echo "Connection string: 127.0.0.1:1521/FREEPDB1"
echo "Admin password: ${ORACLE_PWD}"
echo ""
