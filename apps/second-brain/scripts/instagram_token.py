"""Instagram (Instagram-Login) access-token helper.

Instagram gives you a SHORT-lived token (~1 hour) in the app dashboard. Exchange it for a
LONG-lived token (~60 days), and refresh that before it expires.

  # first time — exchange the short-lived token shown in your Meta app:
  IG_APP_SECRET=... ../.venv/bin/python scripts/instagram_token.py <SHORT_LIVED_TOKEN>

  # every ~60 days — refresh the long-lived token currently in oracle/.env:
  ../.venv/bin/python scripts/instagram_token.py --refresh

Paste the printed token into oracle/.env as IG_ACCESS_TOKEN (keep it secret — it's a credential).
"""
import json
import os
import pathlib
import sys
import urllib.parse
import urllib.request

try:
    from dotenv import load_dotenv
    load_dotenv(pathlib.Path(__file__).resolve().parents[1] / "oracle" / ".env")
except ImportError:
    pass   # shell env still works

BASE = "https://graph.instagram.com"


def _get(path, **params):
    url = f"{BASE}/{path}?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def main():
    args = sys.argv[1:]
    if args and args[0] == "--refresh":
        tok = os.environ.get("IG_ACCESS_TOKEN")
        if not tok:
            sys.exit("set IG_ACCESS_TOKEN (the long-lived token to refresh)")
        d = _get("refresh_access_token", grant_type="ig_refresh_token", access_token=tok)
    elif args:
        secret = os.environ.get("IG_APP_SECRET")
        if not secret:
            sys.exit("set IG_APP_SECRET (from your Meta app > App settings > Basic)")
        d = _get("access_token", grant_type="ig_exchange_token",
                 client_secret=secret, access_token=args[0])
    else:
        sys.exit(__doc__)
    days = int(d.get("expires_in", 0)) // 86400
    token = d.get('access_token') or d.get('token')
    if not token:
        sys.exit(f"unexpected response (no access_token): {d}")
    print(f"\nIG_ACCESS_TOKEN={token}\n\n(valid ~{days} days — paste into oracle/.env, "
          f"then refresh with --refresh before it expires)")


if __name__ == "__main__":
    main()
