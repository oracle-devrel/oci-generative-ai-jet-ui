"""Oracle 26ai connection helper (thin mode — no Oracle client install needed).

Local by default. To point at Oracle Autonomous Database (cloud), set in oracle/.env:
    DB_DSN=<tns_alias>            e.g. mybrain_high  (from the wallet's tnsnames.ora)
    DB_USER=<app_user>           e.g. CCC
    APP_PWD=<password>
    DB_WALLET_DIR=/abs/path/to/wallet     (unzipped Autonomous wallet, has tnsnames.ora + ewallet.pem)
    DB_WALLET_PASSWORD=<wallet password>
With DB_WALLET_DIR set, this connects over mTLS to the cloud; without it, it connects locally.
Nothing else in the codebase changes.
"""
import os
import pathlib

import oracledb
from dotenv import load_dotenv

# Load oracle/.env EXPLICITLY, relative to this file — plain load_dotenv() can't locate it
# during import (its caller-frame walk sees importlib, then falls back to the CWD), so the
# config would only load when running from oracle/agent/. This works from any cwd.
load_dotenv(pathlib.Path(__file__).resolve().parent.parent / ".env")
import keychain_secrets  # noqa: E402
keychain_secrets.resolve_env()   # any keychain:<item> values become real secrets

# CLOB columns come back as str instead of LOB objects.
oracledb.defaults.fetch_lobs = False


def _params():
    # No password fallback, ever: a hardcoded default silently "works" against a DB that happens
    # to use the demo password — fail loudly instead and point at the fix.
    pwd = os.environ.get("APP_PWD")
    if not pwd:
        raise RuntimeError("APP_PWD is not set — copy oracle/.env.example to oracle/.env "
                           "(local demo) or export APP_PWD for your database user.")
    params = dict(
        user=os.environ.get("DB_USER", "CCC"),
        password=pwd,
        dsn=os.environ.get("DB_DSN", "localhost:1521/FREEPDB1"),
    )
    wallet = os.environ.get("DB_WALLET_DIR")
    if wallet:   # Autonomous Database (cloud) — mTLS via wallet
        params.update(
            config_dir=wallet,
            wallet_location=wallet,
            wallet_password=os.environ.get("DB_WALLET_PASSWORD"),
        )
    return params


# A per-process session POOL. The hosted MCP opens a connection per tool call; against a cloud
# Autonomous DB each fresh connect pays TLS + wallet + auth (hundreds of ms) and eats one of the
# Always-Free session slots. A pool amortizes that to ~0, caps concurrent sessions, and keeps a
# session hot (min=1). Every caller keeps the same `connect()` / `.close()` contract — closing a
# pooled connection just returns it to the pool. Set DB_POOL=0 to fall back to direct connects.
_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        _pool = oracledb.create_pool(
            min=1, max=int(os.environ.get("DB_POOL_MAX", "4")), increment=1,
            getmode=oracledb.POOL_GETMODE_WAIT, timeout=300, **_params())
    return _pool


def connect():
    if os.environ.get("DB_POOL", "1") == "0":
        return oracledb.connect(**_params())
    return _get_pool().acquire()
