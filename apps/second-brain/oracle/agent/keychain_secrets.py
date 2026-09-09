"""Keychain-backed secrets: any env var may hold `keychain:<item>` instead of a value.

Instead of putting a raw credential (or a path to a key file) in oracle/.env:

    GDRIVE_KEY=keychain:gdrive-key

...store the secret once in the OS keychain (encrypted at rest, unlocked with
your login session, nothing in plaintext on disk):

    ./.venv/bin/python -c "import keyring; keyring.set_password(
        'second-brain', 'gdrive-key', open('key.json').read())"

`resolve_env()` (called automatically when `db` is imported) replaces every
`keychain:<item>` value in the environment with the stored secret, so loaders
and agents never know the difference. Uses macOS Keychain via the `keyring`
package; on Linux it uses SecretService, on Windows the Credential Locker.

If `keyring` isn't installed or an item is missing, values are left as-is and
a warning is printed — nothing breaks for users who prefer plain .env values.
"""
import os
import sys

SERVICE = "second-brain"
_PREFIX = "keychain:"


def resolve(value):
    """Resolve one value: 'keychain:<item>' -> the stored secret, else unchanged."""
    if not (isinstance(value, str) and value.startswith(_PREFIX)):
        return value
    item = value[len(_PREFIX):]
    try:
        import keyring
        secret = keyring.get_password(SERVICE, item)
    except Exception as e:
        print(f"(secrets: keyring unavailable for '{item}': {e})", file=sys.stderr)
        return value
    if secret is None:
        print(f"(secrets: no keychain item '{item}' under service '{SERVICE}')",
              file=sys.stderr)
        return value
    return secret


def resolve_env():
    """Resolve every keychain: value currently in the environment, in place."""
    for k, v in list(os.environ.items()):
        if isinstance(v, str) and v.startswith(_PREFIX):
            os.environ[k] = resolve(v)


def getenv(name, default=None):
    return resolve(os.environ.get(name, default))
