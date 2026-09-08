#!/bin/bash
# PicoOraClaw OCI Instance Setup Script
# Runs via cloud-init on first boot - fully unattended
set -euo pipefail
exec > >(tee -a /var/log/picooraclaw-setup.log) 2>&1

echo "=== PicoOraClaw setup started at $(date) ==="

ORACLE_MODE="${ORACLE_MODE:-freepdb}"
ORACLE_PWD="${ORACLE_PWD:-PicoOraclaw123}"
ADB_DSN="${ADB_DSN:-}"
ADB_WALLET_BASE64="${ADB_WALLET_BASE64:-}"

# -- 1. System packages --
echo "--- Installing system packages ---"
dnf install -y oracle-epel-release-el9
dnf install -y podman podman-docker git make gcc wget curl unzip python3 zstd
# podman-docker provides 'docker' CLI alias for compatibility

# -- 2. Install Go 1.24 --
echo "--- Installing Go 1.24 ---"
ARCH=$(uname -m)
case "$ARCH" in
  x86_64)  GOARCH="amd64" ;;
  aarch64) GOARCH="arm64" ;;
  *)       GOARCH="$ARCH" ;;
esac
wget -q "https://go.dev/dl/go1.24.0.linux-${GOARCH}.tar.gz" -O /tmp/go.tar.gz
rm -rf /usr/local/go
tar -C /usr/local -xzf /tmp/go.tar.gz
rm /tmp/go.tar.gz
export PATH="/usr/local/go/bin:$PATH"
echo 'export PATH="/usr/local/go/bin:$PATH"' >> /etc/profile.d/golang.sh
go version

# -- 3. Install Ollama --
echo "--- Installing Ollama ---"
curl -fsSL https://ollama.com/install.sh | sh
systemctl enable --now ollama
sleep 5
ollama pull qwen2.5:3b
echo "Ollama ready with qwen2.5:3b"

# -- 4. Build PicoOraClaw --
echo "--- Building PicoOraClaw ---"
git clone https://github.com/jasperan/picooraclaw.git /opt/picooraclaw
cd /opt/picooraclaw
make build
cp "build/picooraclaw-linux-${GOARCH}" /usr/local/bin/picooraclaw
chmod +x /usr/local/bin/picooraclaw
picooraclaw --version || true

# -- 5. Initialize config --
echo "--- Initializing config ---"
export HOME=/home/opc
sudo -u opc picooraclaw onboard <<< "n"

CONFIG_FILE="/home/opc/.picooraclaw/config.json"

# Patch config: set ollama provider and qwen2.5:3b model (supports tool calling)
python3 - "$CONFIG_FILE" <<'PYEOF'
import json, sys
path = sys.argv[1]
with open(path) as f:
    cfg = json.load(f)
cfg["agents"]["defaults"]["provider"] = "ollama"
cfg["agents"]["defaults"]["model"] = "qwen2.5:3b"
with open(path, "w") as f:
    json.dump(cfg, f, indent=2)
PYEOF

# -- 6. Oracle Database Setup --
echo "--- Setting up Oracle Database (mode: $ORACLE_MODE) ---"

if [ "$ORACLE_MODE" = "freepdb" ]; then
  # Pull and start Oracle AI Database 26ai Free container (default backend)
  # gvenzl/oracle-free requires no registry auth (unlike container-registry.oracle.com)
  docker pull docker.io/gvenzl/oracle-free:latest
  docker run -d --name oracle-free \
    -p 1521:1521 \
    -e ORACLE_PASSWORD="$ORACLE_PWD" \
    -e APP_USER=picooraclaw \
    -e APP_USER_PASSWORD="$ORACLE_PWD" \
    -e ORACLE_CHARACTERSET=AL32UTF8 \
    -v oracle-data:/opt/oracle/oradata \
    --restart unless-stopped \
    docker.io/gvenzl/oracle-free:latest

  echo "Waiting for Oracle DB to be ready..."
  TIMEOUT=300
  ELAPSED=0
  while ! docker logs oracle-free 2>&1 | grep -q "DATABASE IS READY TO USE"; do
    sleep 10
    ELAPSED=$((ELAPSED + 10))
    echo "  Waiting... ${ELAPSED}s"
    if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
      echo "ERROR: Oracle DB timed out after ${TIMEOUT}s"
      docker logs oracle-free --tail 50
      exit 1
    fi
  done
  echo "Oracle DB is ready"

  # Grant mining model privilege (user auto-created by gvenzl APP_USER)
  docker exec oracle-free sqlplus -S "sys/${ORACLE_PWD}@localhost:1521/FREEPDB1 as sysdba" <<SQL || true
WHENEVER SQLERROR CONTINUE
GRANT CREATE MINING MODEL TO picooraclaw;
EXIT;
SQL

  # Download and stage ONNX embedding model for VECTOR_EMBEDDING()
  echo "Downloading ONNX embedding model..."
  ONNX_WORK="/tmp/onnx_model"
  mkdir -p "$ONNX_WORK"
  curl -fsSL "https://adwc4pm.objectstorage.us-ashburn-1.oci.customer-oci.com/p/VBRD9P8ZFWkKvnfhrWxkpPe8K03-JIoM5h_8EJyJcpE80c108fuUjg7R5L5O7mMZ/n/adwc4pm/b/OML-Resources/o/all_MiniLM_L12_v2_augmented.zip" \
    -o "$ONNX_WORK/model.zip"
  cd "$ONNX_WORK" && unzip -o model.zip && cd -
  ONNX_FILE=$(find "$ONNX_WORK" -name "*.onnx" -type f | head -1)
  if [ -n "$ONNX_FILE" ]; then
    docker exec oracle-free mkdir -p /opt/oracle/oradata/models
    docker cp "$ONNX_FILE" oracle-free:/opt/oracle/oradata/models/all_MiniLM_L12_v2.onnx
    docker exec oracle-free chown oracle /opt/oracle/oradata/models/all_MiniLM_L12_v2.onnx
    docker exec oracle-free sqlplus -S "sys/${ORACLE_PWD}@localhost:1521/FREEPDB1 as sysdba" <<SQL
CREATE OR REPLACE DIRECTORY PICO_ONNX_DIR AS '/opt/oracle/oradata/models';
GRANT READ ON DIRECTORY PICO_ONNX_DIR TO picooraclaw;
EXIT;
SQL
    echo "ONNX model staged in database"
  else
    echo "WARNING: No .onnx file found in download — embedding will use fallback"
  fi
  rm -rf "$ONNX_WORK"

  # Patch config for freepdb mode
  python3 - "$CONFIG_FILE" "$ORACLE_PWD" <<'PYEOF'
import json, sys
path, pwd = sys.argv[1], sys.argv[2]
with open(path) as f:
    cfg = json.load(f)
cfg.setdefault("oracle", {}).update({
    "enabled": True,
    "mode": "freepdb",
    "host": "localhost",
    "port": 1521,
    "service": "FREEPDB1",
    "user": "picooraclaw",
    "password": pwd,
    "onnxModel": "ALL_MINILM_L12_V2",
    "agentId": "default"
})
with open(path, "w") as f:
    json.dump(cfg, f, indent=2)
PYEOF

elif [ "$ORACLE_MODE" = "adb" ]; then
  # Autonomous AI Database mode (optional cloud backend) - wallet and DSN provided by Terraform
  if [ -n "$ADB_WALLET_BASE64" ]; then
    WALLET_DIR="/home/opc/.picooraclaw/wallet"
    mkdir -p "$WALLET_DIR"
    echo "$ADB_WALLET_BASE64" | base64 -d > "$WALLET_DIR/wallet.zip"
    cd "$WALLET_DIR" && unzip -o wallet.zip && cd -
    chown -R opc:opc "$WALLET_DIR"
  fi

  # Create picooraclaw user in ADB (connect as ADMIN first)
  echo "Creating picooraclaw user in Autonomous Database..."
  pip3 install oracledb 2>/dev/null || pip3 install --break-system-packages oracledb 2>/dev/null || true
  python3 - "$ORACLE_PWD" "$ADB_DSN" "${WALLET_DIR:-}" <<'PYEOF_USER'
import oracledb, sys
pwd, dsn, wallet = sys.argv[1], sys.argv[2], sys.argv[3]
kwargs = {"user": "ADMIN", "password": pwd, "dsn": dsn}
if wallet:
    kwargs.update(config_dir=wallet, wallet_location=wallet, wallet_password=pwd)
conn = oracledb.connect(**kwargs)
cur = conn.cursor()
try:
    cur.execute(f'CREATE USER picooraclaw IDENTIFIED BY "{pwd}" QUOTA UNLIMITED ON DATA')
    print("User picooraclaw created")
except oracledb.DatabaseError as e:
    if "ORA-01920" not in str(e): raise
    print("User picooraclaw already exists")
cur.execute("GRANT CONNECT, RESOURCE, DB_DEVELOPER_ROLE TO picooraclaw")
cur.execute("GRANT CREATE MINING MODEL TO picooraclaw")
conn.commit()
conn.close()
PYEOF_USER

  python3 - "$CONFIG_FILE" "$ORACLE_PWD" "$ADB_DSN" "${WALLET_DIR:-}" <<'PYEOF'
import json, sys
path, pwd, dsn = sys.argv[1], sys.argv[2], sys.argv[3]
wallet_path = sys.argv[4] if len(sys.argv) > 4 else ""
with open(path) as f:
    cfg = json.load(f)
cfg.setdefault("oracle", {}).update({
    "enabled": True,
    "mode": "adb",
    "dsn": dsn,
    "user": "picooraclaw",
    "password": pwd,
    "walletPath": wallet_path,
    "onnxModel": "ALL_MINILM_L12_V2",
    "agentId": "default"
})
with open(path, "w") as f:
    json.dump(cfg, f, indent=2)
PYEOF
fi

# -- 7. Initialize Oracle schema --
echo "--- Running setup-oracle ---"
sudo -u opc picooraclaw setup-oracle

# -- 8. Install and start gateway systemd service --
echo "--- Installing gateway service ---"
cat > /etc/systemd/system/picooraclaw-gateway.service <<'UNIT'
[Unit]
Description=PicoOraClaw Gateway
After=network-online.target ollama.service
Wants=network-online.target

[Service]
Type=simple
User=opc
ExecStart=/usr/local/bin/picooraclaw gateway
Restart=on-failure
RestartSec=10
Environment=HOME=/home/opc

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now picooraclaw-gateway

# -- 9. Done --
echo "=== PicoOraClaw setup completed at $(date) ==="
touch /var/log/picooraclaw-setup-complete
