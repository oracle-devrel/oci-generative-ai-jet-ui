#!/usr/bin/env python3
"""CLI wrapper: invoke a tool from soccer_agent.agent.tools and print JSON."""

from __future__ import annotations

import argparse
import json
import sys

from soccer_agent.agent.tools import dispatch


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("tool")
    p.add_argument("args", help="JSON arg dict")
    p.add_argument("--session", default="toolbelt")
    ns = p.parse_args()

    try:
        args = json.loads(ns.args)
    except json.JSONDecodeError as exc:
        print(json.dumps({"error": f"invalid JSON args: {exc}"}))
        return 1

    result = dispatch(ns.tool, args, session_id=ns.session)
    print(json.dumps(result, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
