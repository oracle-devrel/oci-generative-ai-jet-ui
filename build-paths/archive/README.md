# archive — superseded idea catalog

Ideas the build-paths skill set used to scaffold but no longer does. Kept around in case we revive any of them.

| File | Was | Replaced by |
| --- | --- | --- |
| [`beginner-ideas.md`](./beginner-ideas.md) | Eight CLI-only project ideas (bookmarks, recipes, quotes, movies, smoke, shell history, flashcards, podcast). All Ollama. | Three "X-to-chat" projects on Open WebUI + OCI GenAI Grok 4 (see `beginner/project-ideas.md`). |
| [`intermediate-ideas.md`](./intermediate-ideas.md) | Eight RAG-shaped Gradio projects (PDF-RAG, codebase, web-librarian, slack, markdown, meeting, github, RSS). Mixed Ollama / OCI. | Three Oracle-MCP-driven projects with in-DB ONNX embeddings + Grok 4 (see `intermediate/project-ideas.md`). |
| [`advanced-ideas.md`](./advanced-ideas.md) | Eight DB-as-only-store agent projects (knowledge-OS, spec-to-app, multi-source research, codebase-migration, NL-analyst, CRM, project-copilot, integration-scout). | Three projects composed from the `skills/` building-block library (see `advanced/project-ideas.md`). |

## Why these were cut

The original catalog was breadth-first: hit lots of primitives, give the user maximum choice. Walking it ourselves we hit two problems:

1. **Choice paralysis.** Three paths × eight ideas = 24 first-time decisions. Most users picked option 1 anyway.
2. **Drift between tiers.** Each tier's ideas taught loosely-related things. Hard to write GETTING_STARTED.md that holds together.

The replacement is depth-first per tier:

- **Beginner** — three takes on the same skeleton, varying only the source corpus. Build muscle memory.
- **Intermediate** — three projects all driven by the Oracle MCP server + in-DB embeddings. The whole tier teaches one stack.
- **Advanced** — three projects composed from the same three reusable skills (`skills/`). The point is the composition.

## Reviving an archived idea

If you want any of these back:

1. Read the archive entry (still here, full text).
2. Decide whether it slots into an existing tier (e.g. flashcard-recall could be a beginner variant) or warrants a new tier.
3. Open a PR adding it to the live `project-ideas.md`. Don't move it out of the archive until the PR lands — the archive is the historical record.

The archive is not a graveyard, it's a bench. Things come off the bench when there's a reason.
