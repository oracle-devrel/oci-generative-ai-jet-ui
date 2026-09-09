# sources/ — your canonical content layer

This is where your collected content lands as Markdown + YAML frontmatter — one file per
post/video — created by the collectors in `../scripts/` (e.g. `scripts/youtube.py` writes
`sources/youtube/<id>.md`).

It's the **source of truth**: the Oracle database is a derived, rebuildable view of it.

Per-platform content here is **gitignored** (`sources/*/`) so you don't publish your own
content — generate yours by following the tutorial (`../docs/TUTORIAL.md`).
