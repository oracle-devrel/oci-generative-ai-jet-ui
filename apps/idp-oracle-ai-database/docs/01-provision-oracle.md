# Provision Oracle AI Database (Autonomous)

The rest of the tutorial assumes you have a running Oracle AI Database instance with a wallet downloaded locally. This takes about 5 minutes.

## 1. Sign up for OCI Always Free

`https://www.oracle.com/cloud/free/` — Always Free covers one Autonomous Database, no credit card required for that tier. Pick a home region close to you (this repo was built against `eu-frankfurt-1`).

## 2. Create the database

OCI console → hamburger menu → **Oracle Database** → **Autonomous AI Database** → **Create Autonomous AI Database**.

Settings that matter:

| Field                     | Value                                                                                                                                                                   |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Display name              | `idp` (or anything readable)                                                                                                                                            |
| Workload type             | **Transaction Processing**                                                                                                                                              |
| Always Free               | ON                                                                                                                                                                      |
| Choose database version   | **the latest Oracle AI Database version** (open the dropdown; the default is often `19c`, which does **not** have `VECTOR`, `DBMS_VECTOR_CHAIN`, or JSON Duality Views) |
| Administrator password    | Strong, unique. Save it in a password manager. You will need it for `ORACLE_ADMIN_PASSWORD` in `.env`.                                                                  |
| Access type               | **Secure access from everywhere**                                                                                                                                       |
| Require mutual TLS (mTLS) | Required (auto-set by the previous choice)                                                                                                                              |

> Why "access from everywhere" and not the IP allowlist? Because the deploy target is Lambda, which has no static egress IP unless you put it in a VPC with a NAT Gateway. Lambda + ACL is more friction than Lambda + wallet, and the wallet's mTLS still keeps the database non-public in any meaningful sense.

Click **Create**, wait ~2 minutes for state `Available`.

Verify on the detail page:

- **Database version** is the latest Oracle AI Database release (it must include AI Vector Search). If it says `19c`, terminate and recreate, explicitly selecting the newer version.
- **Mutual TLS (mTLS) authentication** reads `Required`.

## 3. Download the wallet

DB detail page → **Database connection** → **Download wallet**.

- Wallet type: **Instance Wallet** (smaller, single-DB).
- Wallet password: set one (this protects the local files; it is not the ADMIN password). Save it.
- Unzip the downloaded `Wallet_<DBNAME>.zip` to a stable location. Recommended:

  ```bash
  mkdir -p ~/.oci/wallet
  unzip ~/Downloads/Wallet_*.zip -d ~/.oci/wallet
  chmod 600 ~/.oci/wallet/*
  ```

The directory contains `cwallet.sso`, `ewallet.pem`, `tnsnames.ora`, `sqlnet.ora`, etc.

## 4. Get the connect string

Same **Database connection** screen.

- TLS authentication: **Mutual TLS**.
- Copy the connect string for the `_high` service. It looks like:

  ```
  (description= (retry_count=20)(retry_delay=3)(address=(protocol=tcps)(port=1522)(host=adb.<region>.oraclecloud.com))(connect_data=(service_name=<long_id>_<dbname>_high.adb.oraclecloud.com))(security=(ssl_server_dn_match=yes)))
  ```

## 5. Populate `.env`

```bash
cp .env.example .env
```

Fill in:

```
ORACLE_CONNECT_STRING="<the connect string from step 4, wrapped in quotes>"
ORACLE_USER=idp
ORACLE_PASSWORD="<password you'll use for the idp app user>"
ORACLE_ADMIN_PASSWORD="<ADMIN password from step 2>"
ORACLE_WALLET_LOCATION=/Users/<you>/.oci/wallet
ORACLE_WALLET_PASSWORD="<the wallet password from step 3>"
```

Important: any value containing `#`, `$`, `*` or other shell-significant characters must be wrapped in double quotes. `dotenv` treats unquoted `#` as the start of a comment, which silently truncates passwords.

## 6. Bootstrap schema, migrations, and duality views

```bash
pnpm db:setup
```

This runs in two phases:

1. As ADMIN, runs `000_bootstrap.sql` (creates the `idp` user, grants `DB_DEVELOPER_ROLE`, `EXECUTE` on `DBMS_VECTOR` / `DBMS_VECTOR_CHAIN`, `READ, WRITE` on `DATA_PUMP_DIR`).
2. As `idp`, runs `001_schema.sql` (tables, vector index, text index, triggers) and `002_duality_views.sql` (one duality view per doc type + a no-fields top-level view).

After it finishes, you should see `All migrations applied.` and the duality views logged as `✓ CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW ...`.

## 7. Load the ONNX embedding model

One command does both the download and the load:

```bash
pnpm db:setup-onnx
```

Expected output:

```
Phase 1: ADMIN pulls all_MiniLM_L12_v2.onnx into DATA_PUMP_DIR
  ✓ all_MiniLM_L12_v2.onnx = 133322334 bytes

Phase 2: idp loads "doc_embedder" from DATA_PUMP_DIR
  ✓ model doc_embedder loaded
  ✓ embedding dimension = 384
```

> The L12 file is what Oracle publishes as a pre-built ONNX model today. It produces the same 384-dim output as L6, so the schema is unchanged. If you ever need a different file name, set `ONNX_MODEL_FILE` in `.env`.

Next: set up OCI Generative AI for in-database classify + extract. See [02-provision-oci-genai.md](./02-provision-oci-genai.md).

## Troubleshooting

| Symptom                                                         | Cause                                                                                                                                                                                                                    |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `Database version: 19c` on detail page                          | Workload + region defaults to 19c. Terminate, recreate, explicitly pick the latest Oracle AI Database version in the dropdown.                                                                                           |
| `ORA-01017 invalid username/password`                           | Password mismatch. `dotenv` treats `#` as a comment delimiter — quote the value.                                                                                                                                         |
| `NJS-505 unable to initiate TLS connection`, `bad decrypt`      | `ORACLE_WALLET_PASSWORD` missing or wrong. node-oracledb thin mode decrypts `ewallet.pem` and needs the password set at wallet download.                                                                                 |
| `pnpm db:setup` skipping the ADMIN bootstrap phase              | Pass `--skip-bootstrap` only on re-runs when `idp` already exists. The default behavior bootstraps.                                                                                                                      |
| `ORA-40666 qjsngenfullStrmJObj:4` selecting from a duality view | Known Oracle AI Database bug with nested subqueries in duality view projections (as of build 23.26.2.2.0). The repo reads fields directly from `document_fields` instead — see `packages/db/src/repositories/fields.ts`. |
