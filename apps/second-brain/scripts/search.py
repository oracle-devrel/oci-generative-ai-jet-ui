"""Search your brain by meaning, from the terminal.

  ./.venv/bin/python scripts/search.py "protecting data in the cloud"
  ./.venv/bin/python scripts/search.py -k 10 "agent memory"

One query, ranked across all three levels — compiled wiki pages, posts, and
passages inside long content. Lower distance = closer in meaning. The query is
embedded inside the database (no API key, nothing leaves your machine).
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "oracle" / "agent"))
import content  # noqa: E402
import db  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Semantic search over your second brain")
    ap.add_argument("query", help="what to search for, by meaning")
    ap.add_argument("-k", type=int, default=5, help="number of results (default 5)")
    args = ap.parse_args()

    results = content.search_content(db.connect(), args.query, k=args.k)
    if not results:
        print("no matches — is content loaded? (README step 2)")
        return
    for r in results:
        print(f"{r['dist']:.3f}  [{r['lvl']:>7}]  {r['title']}")
        snip = " ".join(str(r.get("snippet") or "").split())
        if snip:
            print(f"                  {snip[:160]}")


if __name__ == "__main__":
    main()
