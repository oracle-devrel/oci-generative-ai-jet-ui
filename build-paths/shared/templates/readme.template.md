# {{project_name}}

> {{one_line_pitch}}
>
> Built with the [`build-paths`](https://github.com/oracle-devrel/oracle-ai-developer-hub/tree/main/build-paths) skill set from Oracle AI Developer Hub. Path: **{{path}}** ({{topic}}).

<!-- Drop a 30s demo GIF or screenshot here. Record with `vhs`, OBS, or your OS. -->
<!-- ![demo](docs/demo.gif) -->

## What this is

{{two_to_three_lines_plain_english}}

## Stack

- **Database** — Oracle 26ai Free, running locally in Docker.
- **Vector store** — `langchain-oracledb` (`OracleVS`) with `{{distance_strategy}}` distance.
- **Embeddings** — `{{embedder_name}}` ({{embedding_dim}} dims).
- **Chat / inference** — {{inference_stack}}.
- **UI** — {{ui_stack_or_none}}.

## Run it (3 commands)

```bash
docker compose up -d --wait              # boot Oracle 26ai Free; ~90s first time
cp .env.example .env                     # already populated by the scaffolding skill
python verify.py                         # green = full stack works end-to-end
python {{entrypoint}}                    # the actual app
```

## Why Oracle AI Database

{{why_oracle_paragraph}}
<!-- Auto-pulled by the skill from shared/references/visual-oracledb-features.md
     based on which features this project uses. -->

## Project layout

```
{{tree}}
```

## What I built (and what I'd do next)

{{user_authored_section}}
<!-- Skill leaves a TODO here for the user to write a 1-paragraph reflection
     before posting. Social-share-quality projects need a human voice. -->

## License

MIT
