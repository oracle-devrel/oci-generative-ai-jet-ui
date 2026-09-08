# Limitless — Claude Code Command Layer

This repo contains real backend scripts for the learning workflow. In Claude Code, do **not** simulate their behavior in chat when the user is asking to run the workflow.

## Rule: run the real scripts

When the user asks for one of the following, you must call the real script and report the real output:

- **XP Builder on `<topic>`**
- **XP Debrief on `<topic>`**
- **Refresh Obsidian**
- **Build framework on `<topic>`**
- **Check learning state on `<topic>`**

For XP Builder specifically, prefer the turn-based backend for Claude Code so the session does not depend on a blocking terminal REPL.

## Required command mapping

### XP Builder

Natural language examples:
- "XP Builder on agent memory"
- "run XP Builder on agent loop"
- "start the XP session for agent memory"

Start the session with:

```bash
python scripts/xp_active.py --json start --topic <topic-slug> --focus <concept-slug>
```

For `agent-memory`, if no focus is specified, prefer `procedural-memory`.

After a session is active, treat the user's next freeform messages as learner answers and continue via the active-session wrapper:

```bash
python scripts/xp_active.py --json answer --answer "<user message>"
```

Claude should then:
1. show the returned `hud` verbatim as the first block
2. read the returned `tutoring_contract`
3. use `response_guidance` as the rendering scaffold
4. produce one natural tutor response
5. present the returned `prompt` exactly once
6. stay on the same concept unless `advance_allowed` is true

Use the active-session wrapper for helper actions too:

```bash
python scripts/xp_active.py --json hint
python scripts/xp_active.py --json status
python scripts/xp_active.py --json finish
```

For every XP return — including `start`, `answer`, `hint`, `status`, and `finish` — always render the backend response in this order:
1. `hud`
2. `tutor_message` or status text
3. `prompt` exactly once if present

Do not omit the `hud`. It carries the persistent session state and the visible helper commands.

The backend will return a structured tutoring contract with:
- diagnosis state
- confidence
- what is correct
- what is missing
- confusions
- pedagogical action mode
- hint / reframe / contrast target
- next prompt
- response guidance for how Claude should render the teaching reply

Use that contract to generate the natural-language tutoring reply in Claude Code.

When rendering the tutor reply, prefer this structure:
1. acknowledge what is right (if anything)
2. use the contract's teaching move
3. ask the next prompt exactly once
4. stay on the same concept unless `advance_allowed` is true
5. do not collapse back into a static questionnaire

Use these backend actions when needed if you are operating without the wrapper:

```bash
python scripts/xp_session.py hint --session-key <session-key> --json
python scripts/xp_session.py status --session-key <session-key> --json
python scripts/xp_session.py finish --session-key <session-key> --json
```

The preferred Claude Code session controls are now:

```bash
python scripts/xp_active.py --json start --topic <topic-slug> --focus <concept-slug>
python scripts/xp_active.py --json answer --answer "<user message>"
python scripts/xp_active.py --json hint
python scripts/xp_active.py --json status
python scripts/xp_active.py --json finish
```

### XP Debrief

Natural language examples:
- "run XP Debrief"
- "debrief the latest agent memory session"
- "XP Debrief on agent loop"

Map to:

```bash
python scripts/run_xp_debrief.py --topic <topic-slug> --latest
```

### Refresh Obsidian

Natural language examples:
- "refresh obsidian"
- "update the vault"
- "project this into obsidian"

Map to:

```bash
python scripts/refresh_obsidian.py
```

### Framework Builder

Natural language examples:
- "build the framework for agent memory"
- "create framework on agent loop"

Map to:

```bash
python scripts/build_framework.py --topic <topic-slug>
```

### Learning-state check

Natural language examples:
- "check learning state for agent memory"
- "show me what is actually in the database for agent loop"

Map to:

```bash
python scripts/check_learning_state.py <topic-slug>
```

## Topic slug normalization

Normalize common topic names like this:

- `agent memory` -> `agent-memory`
- `agent loop` -> `agent-loop`

## Presentation fallback mode

If the user explicitly asks for a **demo mode**, **presentation mode**, or says they want the older smart tutoring behavior back temporarily, use the dedicated fallback commands instead of the real backend:

- `/xp-builder-demo <topic>`
- `/xp-debrief-demo <topic>`

In that mode, you may simulate the tutoring/debrief conversation using the reviewed concept packet, but you must not claim Oracle or Obsidian were updated.

## Tutor-rendering rule

Claude Code should not freestyle the pedagogy when a tutoring contract is available.
Use the returned diagnosis, pedagogical action, response guidance, and `hud` as the source of truth for the next tutor turn.

## Safety rule

Never claim that XP Builder, XP Debrief, Obsidian refresh, or framework generation has run unless the script actually ran and returned output.

If a script fails, show the failure and debug from the real error.

## Preferred workflow

For a real learning loop, the expected backend sequence is:

```bash
python scripts/xp_active.py start --topic agent-memory --focus procedural-memory --json
python scripts/xp_active.py answer --answer "<learner answer>" --json
python scripts/xp_active.py finish --json
python scripts/run_xp_debrief.py --topic agent-memory --latest
python scripts/refresh_obsidian.py
```
