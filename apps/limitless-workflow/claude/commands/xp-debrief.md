Run the real Limitless XP Debrief backend instead of simulating scoring in chat.

Arguments: `$ARGUMENTS`

## Behavior

- Normalize topic names like `agent memory` -> `agent-memory`
- If no topic is provided, ask for one
- Debrief the latest transcript for that topic unless a transcript path is explicitly supplied
- Run the backend script and return the real output

## Command

```bash
python scripts/run_xp_debrief.py --topic <topic-slug> --latest
```

## Important

Do not summarize what you think the score would be. Run the real script and show the actual concept updates.
