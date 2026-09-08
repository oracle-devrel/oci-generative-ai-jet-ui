Run the real Limitless XP Builder backend instead of simulating the session.

Arguments: `$ARGUMENTS`

## Behavior

- Normalize topic names like `agent memory` -> `agent-memory`
- If the topic is `agent-memory` and no focus is provided, use `procedural-memory`
- If a second argument is provided, treat it as the focus concept
- Start the session through the turn-based backend and return the real output
- Once a session is active, continue it through the active-session wrapper so Claude Code does not have to carry the raw `session_key` manually

## Start command

Default for agent memory:

```bash
python scripts/xp_active.py --json start --topic agent-memory --focus procedural-memory
```

Generic form:

```bash
python scripts/xp_active.py --json start --topic <topic-slug>
python scripts/xp_active.py --json start --topic <topic-slug> --focus <concept-slug>
```

## Continue commands during the session

```bash
python scripts/xp_active.py --json answer --answer "<learner answer>"
python scripts/xp_active.py --json hint
python scripts/xp_active.py --json status
python scripts/xp_active.py --json finish
```

## Turn-by-turn orchestration rule

When an XP session is active:

1. treat the user's normal next reply as the learner answer
2. run:
   ```bash
   python scripts/xp_active.py --json answer --answer "<learner answer>"
   ```
3. read the returned `tutoring_contract`
4. use `response_guidance` to shape the tutor reply
5. show the contract's `prompt` exactly once
6. do not jump to another concept unless the backend allows it

## Rendering rule

For every XP return — including `start`, `answer`, `hint`, `status`, and `finish` — render the backend response in this order:

1. show the returned `hud` verbatim as the first block
2. show the returned `tutor_message` or status text
3. show the returned `prompt` exactly once if present

Never omit the `hud`. It is the persistent session header and helper strip the user relies on to see the current concept and available commands.

## Important

Do not simulate the session in chat. Run the backend and use the returned `hud`, tutoring contract, prompt, tutor message, and status fields to drive the conversation.
If normal freeform continuation is unreliable, fall back to:

```text
/xp-answer <learner answer>
```
