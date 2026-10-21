"""Create only this demo's credentials; never print or copy provider secrets."""
import secrets
from pathlib import Path

root = Path(__file__).resolve().parent.parent
p = root / ".env"
if not p.exists():
    lines = [
        "HF_DSN=localhost:1523/FREEPDB1",
        "HF_DB_CONTAINER=hf-oracle",
        "HF_DB_PORT=1523",
        "HF_DEFAULT_MODEL=ollama",
        "OLLAMA_URL=http://127.0.0.1:11434",
        "PRIVATE_AI_URL=https://127.0.0.1:8443",
    ]
    for name in ["OWNER", "CREDIT", "MARKETS"]:
        lines.append(f"HF_{name}_PASSWORD=Hf{secrets.token_hex(18)}")
    p.write_text("\n".join(lines) + "\n")
    p.chmod(0o600)
    print("Created .env with isolated demo database credentials")
