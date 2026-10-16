# Git Second Brain — Database

SQL scripts for setting up the Oracle AI Database 26ai schema used by the
data loader and the app.

## Prerequisites

- Oracle AI Database 26ai (e.g. the free container image)
- A DBA connection to the target PDB (e.g. `SYSTEM`)

## Scripts

Run in order:

| Script                 | Run as                        | Purpose                                                                         |
| ---------------------- | ----------------------------- | ------------------------------------------------------------------------------- |
| `01_create_user.sql`   | SYS / SYSTEM                  | Creates the `GITHUB_SECOND_BRAIN` user with required grants                     |
| `02_create_schema.sql` | SYSTEM or GITHUB_SECOND_BRAIN | Creates the `FASTAPI_COMMITS` table, indexes, and (optionally) the vector index |

## Usage

```bash
# Connect as SYSTEM to the pluggable database
sqlplus system/Welcome_123@//localhost:1521/FREEPDB1

# Then run each script
@01_create_user.sql
@02_create_schema.sql
```

> **Note:** The vector index creation is commented out in `02_create_schema.sql`.
> Create it **after** loading data with `data-loader/` for faster build times
> and better index quality.
