"""Ingest your Instagram content + performance into the brain via the **Instagram API with
Instagram Login** (Creator/Business account — no Facebook Page needed).

Setup (one-time, in your Meta app — see docs/EXPORT_GUIDE.md):
  - create a Meta app, add "Instagram" > "API setup with Instagram login"
  - connect your Creator account, grant instagram_business_basic + instagram_business_manage_insights
  - exchange the short-lived token for a long-lived one:  scripts/instagram_token.py
Then set in oracle/.env:
  IG_ACCESS_TOKEN=<long-lived token>     (refresh ~every 60 days: scripts/instagram_token.py --refresh)

Run:  ./.venv/bin/python scripts/instagram.py         # incremental: only adds new media
Instagram content is CONTENT (visibility='content'); engagement/reach are kept as a content signal.
"""
import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "oracle", "agent"))
import db  # noqa: E402

API = "https://graph.instagram.com"
VER = os.environ.get("IG_API_VERSION", "v23.0")
TOKEN = os.environ.get("IG_ACCESS_TOKEN")
MEDIA_FIELDS = ("id,caption,media_type,media_product_type,permalink,timestamp,"
                "like_count,comments_count,thumbnail_url")
KIND = {"REELS": "reel", "CAROUSEL_ALBUM": "carousel", "STORY": "story"}


def _get_url(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def _get(path, **params):
    params["access_token"] = TOKEN
    return _get_url(f"{API}/{VER}/{path}?" + urllib.parse.urlencode(params))


def _media_pages():
    """Yield every media item, following Instagram's paging.next (which carries the token)."""
    url = f"{API}/{VER}/me/media?" + urllib.parse.urlencode(
        {"fields": MEDIA_FIELDS, "limit": 100, "access_token": TOKEN})
    while url:
        page = _get_url(url)
        for m in page.get("data", []):
            yield m
        url = page.get("paging", {}).get("next")


def _kind(m):
    return KIND.get(m.get("media_product_type")) or \
        {"IMAGE": "post", "VIDEO": "video", "CAROUSEL_ALBUM": "carousel"}.get(m.get("media_type"), "post")


def _views(media_id):
    """Best-effort reach/views (a content signal, not financial). Never fatal."""
    for metrics in ("views,reach", "reach"):
        try:
            data = _get(f"{media_id}/insights", metric=metrics, period="lifetime")
            vals = {d["name"]: d["values"][0]["value"] for d in data.get("data", [])}
            return vals.get("views") or vals.get("reach")
        except Exception:
            continue
    return None


def main():
    if not TOKEN:
        sys.exit("set IG_ACCESS_TOKEN (see scripts/instagram_token.py)")
    conn = db.connect()
    cur = conn.cursor()
    cur.execute("merge into platforms p using (select 'instagram' id from dual) s "
                "on (p.platform_id=s.id) when not matched then "
                "insert (platform_id, display_name) values ('instagram','Instagram')")
    cur.execute("select url from posts where platform_id='instagram' and url is not null")
    seen = {r[0] for r in cur.fetchall()}

    added = 0
    for m in _media_pages():
        link = m.get("permalink")
        if not link or link in seen:
            continue
        cap = (m.get("caption") or "").strip()
        title = cap.split("\n", 1)[0][:200] or f"Instagram {m.get('media_type', '').lower()}"
        cur.execute(
            """insert into posts (platform_id, kind, title, caption, url, published_at,
                   likes, comments, views, visibility, content_embedding)
               values ('instagram', :kind, :title, :caption, :url,
                   to_timestamp_tz(:ts,'YYYY-MM-DD"T"HH24:MI:SS TZHTZM'),
                   :likes, :comments, :views, 'content',
                   vector_embedding(MINILM using :emb as data))""",
            kind=_kind(m), title=title, caption=cap[:4000], url=link, ts=m.get("timestamp"),
            likes=m.get("like_count") or 0, comments=m.get("comments_count") or 0,
            views=_views(m["id"]), emb=(f"{title}. {cap}")[:3000],
        )
        seen.add(link)
        added += 1
        if added % 25 == 0:
            conn.commit()
            print(f"  +{added} new media...")
    conn.commit()
    n = cur.execute("select count(*) from posts where platform_id='instagram'").fetchone()[0]
    print(f"added {added} new Instagram posts (total now {n})")
    conn.close()


if __name__ == "__main__":
    main()
