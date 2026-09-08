Show the active XP session status from the real backend.

Arguments: `$ARGUMENTS`

## Command

```bash
python scripts/xp_active.py --json status
```

## Rendering rule

After running the backend, always show the returned `hud` verbatim first. If additional status text is returned, show it under the `hud`.

## Important

This only works if an XP session is already active.
