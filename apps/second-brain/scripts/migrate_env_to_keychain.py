"""Move plaintext secrets from oracle/.env into the macOS Keychain, leaving a
`keychain:<item>` pointer behind. Same mechanism as the already-migrated
GDRIVE_KEY / APIFY_TOKEN (resolved at runtime by oracle/agent/keychain_secrets.py).

WHY: a plaintext .env is readable by any process that can read the repo dir and
trivially leaks via backups/screen-shares. The Keychain is encrypted at rest and
unlocked only by your login session. Pointers stay in .env; secrets don't.

YOU run this (agents are hook-blocked from writing .env, by design). It never
prints secret values. It is idempotent and re-runnable.

  # see exactly what would move (no values shown), nothing changes:
  ./.venv/bin/python scripts/migrate_env_to_keychain.py

  # do it (backs up .env first, verifies each secret reads back, then rewrites):
  ./.venv/bin/python scripts/migrate_env_to_keychain.py --apply

  # confirm every keychain: pointer in .env still resolves:
  ./.venv/bin/python scripts/migrate_env_to_keychain.py --verify

ROTATION (separate, optional, your call at each provider): after migrating, you
can rotate a high-blast key — generate a new one at the provider, then re-store
it without touching .env:
  ./.venv/bin/python -c "import keyring; keyring.set_password('second-brain','anthropic-api-key','<new>')"
"""
import datetime
import os
import pathlib
import re
import shutil
import sys

SERVICE = "second-brain"
ENV_PATH = pathlib.Path(__file__).resolve().parent.parent / "oracle" / ".env"

# Curated allowlist — real secrets only. Deliberately EXCLUDES paths/usernames/
# config that a naive TOKEN|KEY match would mis-handle:
#   DB_WALLET_DIR (a path), DB_USER (username), DB_DSN (TNS alias, not a secret),
#   and all the GDRIVE_*/NOTION_DEAL_*/*_URL config knobs.
# ORACLE_PWD / APP_PWD are here on purpose — they are passwords ("PWD"), which a
# keyword filter looking for PASSWORD would miss.
# Every key here has a LOCAL consumer that runs the resolver (db.py import,
# llm.py, or keychain_secrets.getenv), so a keychain: pointer resolves before use.
SECRET_KEYS = [
    "ORACLE_PWD",           # db.py resolves on import
    "APP_PWD",              # db.py
    "DB_WALLET_PASSWORD",   # db.py
    "ANTHROPIC_API_KEY",    # llm.py resolves; consolidate imports db
    "OPENAI_API_KEY",       # llm.py
    "NOTION_TOKEN",         # notion.py imports db before reading it
    "GEMINI_API_KEY",       # gemini_video.py uses keychain_secrets.getenv()
]
# DELIBERATELY EXCLUDED — verify the consumer resolves keychain: BEFORE adding:
#   EXCALIDRAW_API_KEY — no local Python reads it; it is consumed by the Fly
#     hosted server / deploy path, which would receive the literal "keychain:..."
#     string, not the secret. Migrate only after that path is confirmed to resolve
#     (or manage it as a Fly secret and drop it from local .env entirely).

KC_PREFIX = "keychain:"


def item_for(key):
    """ANTHROPIC_API_KEY -> anthropic-api-key (matches the gdrive-key convention)."""
    return key.lower().replace("_", "-")


def load_parsed():
    """Parse .env with the SAME semantics the app uses (quote-stripping, escapes),
    so a stored value resolves byte-identical to what load_dotenv() produces."""
    try:
        from dotenv import dotenv_values
    except Exception as e:
        sys.exit(f"python-dotenv not importable ({e}); run with ./.venv/bin/python")
    return dotenv_values(ENV_PATH)


def require_keyring():
    try:
        import keyring
        return keyring
    except Exception as e:
        sys.exit(f"keyring not importable ({e}); run with ./.venv/bin/python")


def classify(parsed):
    """Return list of (key, status) where status is one of:
    will-migrate | already-keychain | empty-or-absent."""
    rows = []
    for key in SECRET_KEYS:
        raw = parsed.get(key)
        if raw is None or raw == "":
            rows.append((key, "empty-or-absent"))
        elif raw.startswith(KC_PREFIX):
            rows.append((key, "already-keychain"))
        else:
            rows.append((key, "will-migrate"))
    return rows


def cmd_dry_run(parsed):
    rows = classify(parsed)
    print(f"env: {ENV_PATH}")
    print("Secrets (values never shown):\n")
    for key, status in rows:
        note = f"  ->  {key}=keychain:{item_for(key)}" if status == "will-migrate" else ""
        print(f"  {key:<22} {status}{note}")
    n = sum(1 for _, s in rows if s == "will-migrate")
    print(f"\n{n} would migrate. Re-run with --apply to do it (backs up .env first).")
    if n == 0:
        print("Nothing to do — already migrated or unset.")


def cmd_apply(parsed):
    keyring = require_keyring()
    todo = [k for k, s in classify(parsed) if s == "will-migrate"]
    if not todo:
        print("Nothing to migrate. (Already keychain: pointers or unset.)")
        return

    # 1) Back up .env (0600) before any change.
    stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    backup = ENV_PATH.with_name(f".env.bak-{stamp}")
    shutil.copy2(ENV_PATH, backup)
    os.chmod(backup, 0o600)
    print(f"backed up .env -> {backup.name} (0600)")

    # 2) Store each secret, then read it back and confirm it matches BEFORE we
    #    agree to rewrite that line. If a round-trip fails, we skip that key and
    #    leave its plaintext untouched — never lose a secret.
    verified = []
    for key in todo:
        item = item_for(key)
        value = parsed[key]
        keyring.set_password(SERVICE, item, value)
        if keyring.get_password(SERVICE, item) == value:
            verified.append(key)
            print(f"  stored + verified: {key} -> keychain:{item}")
        else:
            print(f"  !! round-trip FAILED for {key} — leaving it in .env, skipping",
                  file=sys.stderr)

    if not verified:
        print("No secret verified; .env left unchanged.", file=sys.stderr)
        return

    # 3) Rewrite only the verified lines, preserving everything else exactly.
    text = ENV_PATH.read_text()
    for key in verified:
        pattern = re.compile(rf"^(\s*{re.escape(key)}\s*=).*$", re.MULTILINE)
        text = pattern.sub(lambda m: f"{key}=keychain:{item_for(key)}", text, count=1)
    ENV_PATH.write_text(text)
    print(f"\nrewrote {len(verified)} line(s) in .env to keychain: pointers.")
    print("verify with:  ./.venv/bin/python scripts/migrate_env_to_keychain.py --verify")


def cmd_verify(parsed):
    keyring = require_keyring()
    missing = 0
    print("Resolving every keychain: pointer in .env (values never shown):\n")
    for key, raw in parsed.items():
        if isinstance(raw, str) and raw.startswith(KC_PREFIX):
            item = raw[len(KC_PREFIX):]
            ok = keyring.get_password(SERVICE, item) is not None
            print(f"  {key:<22} keychain:{item:<22} {'OK' if ok else 'MISSING'}")
            missing += 0 if ok else 1
    if missing:
        sys.exit(f"\n{missing} pointer(s) do not resolve — check the item names.")
    print("\nAll pointers resolve.")


def main():
    if not ENV_PATH.exists():
        sys.exit(f"no .env at {ENV_PATH}")
    parsed = load_parsed()
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "--apply":
        cmd_apply(parsed)
    elif arg == "--verify":
        cmd_verify(parsed)
    elif arg in ("", "--dry-run"):
        cmd_dry_run(parsed)
    else:
        sys.exit(f"unknown arg {arg!r}; use (nothing) | --apply | --verify")


if __name__ == "__main__":
    main()
