"""ccctx: register, ingest and inspect codebases (contracts/cli.md). Exit 0 ok, 1 refused input, 2 database down.

`main` parses the arguments, refuses bad input before touching the database, connects, migrates and runs the
command.
"""

import logging
import re
import sys

import oracledb

from golestan_code_mcp import db, registry, schema
from golestan_code_mcp.cli import index_commands, search_commands
from golestan_code_mcp.cli import parser as cli_parser
from golestan_code_mcp.config import load
from golestan_code_mcp.graph import queries
from golestan_code_mcp.indexing import ingest as indexing_ingest
from golestan_code_mcp.indexing.files import IngestError
from golestan_code_mcp.memory import store as memory_store
from golestan_code_mcp.search import query
from golestan_code_mcp.wiki import build


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # a docstring's character the console cannot show must not end the run
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    args = cli_parser.parser().parse_args(argv)
    if args.group == "mcp":  # before connecting: the server reports an outage per call
        from golestan_code_mcp.server import (
            app,  # only this command needs the MCP library
        )

        app.main()
        return 0
    handler = logging.StreamHandler(sys.stderr)  # the structured ingest and wiki records go to stderr
    for log in (indexing_ingest.log, build.log, memory_store.log):
        log.addHandler(handler)
        log.setLevel(logging.INFO)
    conn = None
    try:
        if args.run is index_commands._repo_add:  # refuse bad input before touching the database
            registry.validate_name(args.name)
            registry.resolve_dir(args.path)
        if args.run is search_commands._search:  # refuse bad input before touching the database
            if not args.question.strip():
                raise ValueError("the question is empty")
            if args.mode not in query.MODES:
                raise ValueError(f"unknown mode '{args.mode}'; valid modes: {', '.join(query.MODES)}")
            args.limit = query.check_limit(int(args.limit) if re.fullmatch(r"-?[0-9]+", args.limit) else None)
            query.check_language(args.language)
        if args.run in search_commands.GRAPH:  # refuse bad input before touching the database
            queries.check_name(args.name)
            if args.run is search_commands._impact:  # a bad --depth exits 1, not argparse's 2
                args.depth = queries.check_depth(int(args.depth) if re.fullmatch(r"-?[0-9]+", args.depth) else None)
        conn = db.connect(load())
        with conn:
            if args.run is not index_commands._db_migrate:
                schema.migrate(conn)
            print(args.run(conn, args))
    except (ValueError, IngestError) as e:  # ConfigError, RegistryError and ModelError are ValueErrors
        print(f"error: {e}", file=sys.stderr)
        return 1
    except oracledb.Error as e:
        code = getattr(e.args[0], "full_code", "")
        if code in db.STARTING_CODES:
            reason = "database is still starting"
        else:  # a failure after connecting is not an outage
            reason = f"database {'error' if conn else 'unreachable'}: {db.describe(e)}"
        print(f"error: {reason}", file=sys.stderr)
        return 2
    finally:
        for log in (indexing_ingest.log, build.log, memory_store.log):
            log.removeHandler(handler)
    return 0
