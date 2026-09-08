"""Collect step (LinkedIn): scheduled self-scrape of YOUR OWN public posts via a
pinned Apify actor — LinkedIn has no API for your own posts, so this reads your
public profile the way a logged-out visitor would. NO login, NO cookies, ever.

Config (oracle/.env):
  APIFY_TOKEN=keychain:apify-token        # the sync step is skipped when unset
  LINKEDIN_PROFILE_URL=https://www.linkedin.com/in/<your-handle>/

Hardening (each line here is deliberate — adapt, don't delete):
  - The actor is PINNED BY IMMUTABLE ID (not name search) — swapping actors is a
    reviewed code change, not a lookup surprise.
  - The ONLY target is the configured profile URL — a constant, never derived
    from data. Recon of other profiles is a supervised, on-demand thing.
  - Every returned post must be AUTHORED BY the configured handle; if none are,
    nothing is ingested and the step FAILS (guards against actor bugs/swaps
    poisoning your voice corpus with someone else's posts).
  - Only an allowlist of fields is ingested (text, date, url); everything else
    the actor returns is dropped. Text is length-capped. Scraped content is
    data, never instructions.
  - Fail-closed: credit exhaustion, HTTP errors, and empty/foreign payloads all
    exit non-zero, which lands in the sync heartbeat -> health panel -> alert.
  - Weekly cadence: the daily sync calls this, but it no-ops unless >=7 days
    since the last successful scrape (keeps actor spend at cents/month).
  - Dedupe by post URL: delete-then-insert, idempotent re-runs.
"""
import datetime
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "oracle" / "agent"))
import db  # noqa: E402  (also resolves keychain:<item> env values)

ACTOR_ID = "A3cAPGpwBEG8RJwse"   # harvestapi/linkedin-profile-posts (no-cookie, pay-per-event)
API = f"https://api.apify.com/v2/acts/{ACTOR_ID}/run-sync-get-dataset-items"
MAX_POSTS = 50
POSTED_LIMIT = "month"
CADENCE_DAYS = 7
MARKER = ROOT / "exports" / ".linkedin_scrape_last"
MIN_TEXT = 25


def handle_of(profile_url):
    """Pure: the /in/<handle> from a profile URL, lowercased ('' if not found)."""
    m = re.search(r"/in/([^/?#]+)", profile_url or "")
    return (m.group(1) if m else "").lower()


def parse_items(items, expected_handle):
    """Pure: actor output -> [{url, text, title, published_at}] for posts that are
    (a) authored by expected_handle, (b) real posts with a URL and enough text.
    Everything else — other authors, junk, extra fields — is dropped here."""
    out = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        author = (it.get("author") or {}).get("publicIdentifier") or ""
        if author.lower() != expected_handle:
            continue
        url = (it.get("linkedinUrl") or "").split("?")[0].strip()
        text = (it.get("content") or "").strip()
        if not url or len(text) < MIN_TEXT:
            continue
        raw_date = (it.get("postedAt") or {}).get("date")
        published = None
        if raw_date:
            try:
                published = datetime.datetime.fromisoformat(
                    raw_date.replace("Z", "+00:00")).replace(tzinfo=None)
            except ValueError:
                published = None
        out.append({"url": url[:600], "text": text[:4000],
                    "title": text.split("\n", 1)[0][:150], "published_at": published})
    return out


def ran_recently():
    try:
        last = datetime.date.fromisoformat(MARKER.read_text().strip())
        return (datetime.date.today() - last).days < CADENCE_DAYS
    except Exception:
        return False


def main():
    token = os.environ.get("APIFY_TOKEN")
    profile = os.environ.get("LINKEDIN_PROFILE_URL", "")
    expected = handle_of(profile)
    if not token or not expected:
        sys.exit("linkedin_apify: set APIFY_TOKEN and LINKEDIN_PROFILE_URL "
                 "(https://www.linkedin.com/in/<handle>/) in oracle/.env")
    if ran_recently():
        print(f"linkedin scrape ran <{CADENCE_DAYS}d ago — nothing to do (weekly cadence)")
        return
    import requests
    # token travels in the Authorization header, never the URL (query strings land in logs)
    r = requests.post(API, params={"timeout": 180},
                      headers={"Authorization": f"Bearer {token}"},
                      json={"targetUrls": [profile], "maxPosts": MAX_POSTS,
                            "postedLimit": POSTED_LIMIT, "includeReposts": False},
                      timeout=300)
    if r.status_code == 402 or "insufficient" in r.text[:500].lower():
        sys.exit("linkedin_apify: Apify CREDIT EXHAUSTED — top up or wait for the "
                 "monthly reset (free plan). The scrape will resume on its own after.")
    if r.status_code not in (200, 201):
        sys.exit(f"linkedin_apify: actor run failed HTTP {r.status_code}: {r.text[:200]}")
    items = r.json()
    posts = parse_items(items, expected)
    if items and not posts:
        sys.exit(f"linkedin_apify: actor returned {len(items)} items but NONE authored "
                 f"by '{expected}' — refusing to ingest (actor changed or wrong target?)")
    conn = db.connect()
    cur = conn.cursor()
    cur.execute("alter session disable parallel dml")
    cur.execute("merge into platforms p using (select 'linkedin' id from dual) s "
                "on (p.platform_id=s.id) when not matched then "
                "insert (platform_id, display_name) values ('linkedin','LinkedIn')")
    n = 0
    for p in posts:
        cur.execute("delete from posts where url = :u", u=p["url"])
        cur.execute(
            """insert into posts (platform_id, kind, title, caption, url, published_at,
                   visibility, content_embedding)
               values ('linkedin', 'post', :t, :c, :u, :p, 'content',
                   vector_embedding(MINILM using :e as data))""",
            t=p["title"], c=p["text"], u=p["url"], p=p["published_at"],
            e=(p["title"] + ". " + p["text"])[:3000])
        n += 1
    conn.commit()
    total = cur.execute(
        "select count(*) from posts where platform_id='linkedin'").fetchone()[0]
    conn.close()
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.write_text(datetime.date.today().isoformat())
    print(f"ingested/refreshed {n} LinkedIn posts (of {len(items)} scraped); "
          f"total linkedin now {total}")


if __name__ == "__main__":
    main()
