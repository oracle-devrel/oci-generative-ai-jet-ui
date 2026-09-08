Send the learner's next answer into the currently active XP session.

Arguments: `$ARGUMENTS`

## Command

```bash
python scripts/xp_active.py --json answer --answer "$ARGUMENTS"
```

## Use

This is a fallback when the active XP session should continue explicitly instead of relying on freeform reply routing.

## Rendering rule

After running the backend, render the response in this order:

1. show the returned `hud` verbatim
2. show the returned `tutor_message`
3. show the returned `prompt` exactly once if present

## Important

Only use this if an XP session is already active.
Do not simulate the answer handling in chat — run the backend and use the returned `hud` and tutoring contract.
