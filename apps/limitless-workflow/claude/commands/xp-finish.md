Finish the active XP session using the real backend.

Arguments: `$ARGUMENTS`

## Command

```bash
python scripts/xp_active.py --json finish
```

## Rendering rule

After running the backend, show the returned `hud` first if present, then show the finish confirmation and any transcript/session path details.

## Important

This closes the active session and clears the active-session pointer file.
