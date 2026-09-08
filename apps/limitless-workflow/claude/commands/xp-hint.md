Use the active XP session and request a hint from the real backend.

Arguments: `$ARGUMENTS`

## Command

```bash
python scripts/xp_active.py --json hint
```

## Rendering rule

After running the backend, render the response in this order:

1. show the returned `hud` verbatim
2. show the returned `tutor_message`
3. show the returned `prompt` exactly once if present

## Important

This only works if an XP session is already active.
Do not simulate the hint. Use the backend response.
