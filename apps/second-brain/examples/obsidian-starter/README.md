# Obsidian starter vault (or any drop folder)

A minimal template for connecting an Obsidian vault — or any plain folder — to your
second brain. Two ways to use it:

1. **Already have a vault?** You don't need this template — just set
   `OBSIDIAN_VAULT=/path/to/your/vault` in `oracle/.env`. The loader reads your
   existing notes as they are (and PDFs/EPUBs too).
2. **Starting fresh?** Copy this folder somewhere (e.g. `~/Documents/Brain`),
   open it in Obsidian as a vault (optional — the folder works without the app),
   and set `OBSIDIAN_VAULT` to its path.

Then either run `./.venv/bin/python scripts/obsidian.py` or let the daily sync
(Lab 6) pick it up automatically.

## What syncs, and how

| You drop | It becomes |
|---|---|
| `.md` / `.txt` | a searchable note (frontmatter respected — see below) |
| `.pdf` / `.epub` | full text, chunked, as **reference material**: searchable when you ask, excluded from the wiki compiler — your wiki synthesizes *your* work, not your library |

Edited files re-import in place; unchanged files are skipped; `.obsidian/`,
`.trash/` and `templates/` folders are ignored.

## Frontmatter (all optional)

```yaml
---
title: Overrides the filename
tags: ml, reading            # searchable
series: courses              # groups notes — "list everything in my courses series"
visibility: private          # keeps THIS note out of the searchable brain entirely
created: 2026-07-01
---
```

## Folder philosophy

Keep it simple — folders are for your eyes; the loader only reads frontmatter.
This template ships just `notes/` and `books/`. If you want more structure,
the PARA method (Projects / Areas / Resources / Archive) is the common
convention — but don't build a parallel wiki in here: the database's compiled
wiki already does that job, and better.
