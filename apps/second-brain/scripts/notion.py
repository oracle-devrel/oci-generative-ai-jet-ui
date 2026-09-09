"""Collect step (Notion): your content calendar + planning/brand pages -> the brain.

Pulls every page the integration can access (calendar rows are pages too), captures the
editorial properties (Type / Status / Publication Date / Link / Category), chunks the page
body, and sets the PAID/brand flag from Type/Category. LOCAL only.

Setup: NOTION_TOKEN in oracle/.env; the integration connected to your pages (••• -> Connections).
Run from repo root:  ./.venv/bin/python scripts/notion.py
"""
import datetime
import os
import pathlib

import oracledb
from dotenv import load_dotenv
from notion_client import Client

ROOT = pathlib.Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "oracle" / ".env")
import sys
sys.path.insert(0, str(ROOT / "oracle" / "agent"))
import db  # noqa: E402  (wallet-aware connect — works for local AND cloud)

oracledb.defaults.fetch_lobs = False
if not os.environ.get("NOTION_TOKEN"):
    raise SystemExit("NOTION_TOKEN is not set. Create an internal integration at "
                     "notion.so/my-integrations, share your pages with it, and put "
                     "NOTION_TOKEN=... in oracle/.env (see docs/EXPORT_GUIDE.md).")
notion = Client(auth=os.environ["NOTION_TOKEN"])

# Private brand-deal financials stay OUT of the content brain by default; opt in only for a
# full LOCAL vault (never point this at the hosted/cloud content brain).
INCLUDE_BUSINESS = os.environ.get("BRAIN_INCLUDE_BUSINESS") == "1"

# YOUR tracker schemas live in oracle/.env (gitignored) — the defaults below are generic
# examples. NOTION_DEAL_PROPS: comma-separated property names of YOUR deal tracker (a page
# matching >=2 of them is treated as private business data and skipped). NOTION_DEAL_DATES:
# date property names to try for a deal's publish date. NOTION_SERIES_CHECKBOX: a boolean
# column whose checked pages get series=<its name, snake_cased>.
DEAL_PROPS = {p.strip() for p in os.environ.get(
    "NOTION_DEAL_PROPS", "Payment Status,Rate,Fee,Deliverables,Contract").split(",") if p.strip()}
DEAL_DATE_PROPS = [p.strip() for p in os.environ.get(
    "NOTION_DEAL_DATES", "Published Date,Deadline").split(",") if p.strip()]
SERIES_CHECKBOX = os.environ.get("NOTION_SERIES_CHECKBOX", "").strip()
SERIES_FROM_CHECKBOX = SERIES_CHECKBOX.lower().replace(" ", "_")[:20] or None


def connect():
    return db.connect()


def rich(arr):
    return "".join(s.get("plain_text", "") for s in (arr or []))


def title_of(props):
    for v in props.values():
        if v.get("type") == "title":
            return rich(v.get("title"))
    return ""


def sel(props, name):
    v = props.get(name)
    return v["select"]["name"] if v and v.get("type") == "select" and v.get("select") else None


def date_of(props, *names):
    for name in names:
        v = props.get(name)
        if v and v.get("type") == "date" and v.get("date"):
            return v["date"].get("start")
    return None


def url_of(props, name):
    v = props.get(name)
    return v.get("url") if v and v.get("type") == "url" else None


def iso(s):
    if not s:
        return None
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        try:
            return datetime.datetime.strptime(s[:10], "%Y-%m-%d")
        except Exception:
            return None


def body_text(page_id, cap=80):
    out, cursor, count = [], None, 0
    while True:
        r = notion.blocks.children.list(block_id=page_id, start_cursor=cursor, page_size=100)
        for b in r.get("results", []):
            data = b.get(b.get("type"), {})
            if isinstance(data, dict) and data.get("rich_text"):
                out.append(rich(data["rich_text"]))
            count += 1
        if count >= cap or not r.get("has_more"):
            break
        cursor = r.get("next_cursor")
    return "\n".join(x for x in out if x.strip())


def chunks_of(text, size=1500):
    out, buf = [], ""
    for para in text.split("\n"):
        if buf and len(buf) + len(para) + 1 > size:
            out.append(buf)
            buf = para
        else:
            buf = f"{buf}\n{para}" if buf else para
    if buf.strip():
        out.append(buf)
    return out


def main():
    conn = connect()
    cur = conn.cursor()
    cur.execute("alter session disable parallel dml")   # Autonomous DB: allow delete+insert in one txn
    cur.execute("merge into platforms p using (select 'notion' id from dual) s "
                "on (p.platform_id=s.id) when not matched then "
                "insert (platform_id, display_name) values ('notion','Notion')")
    cur.execute("delete from posts where platform_id='notion'")
    # NO commit here: delete + reload is ONE transaction (a mid-run Notion API
    # failure leaves the previous content intact).

    n, total_chunks, skipped_business, cursor = 0, 0, 0, None
    while True:
        r = notion.search(page_size=100, start_cursor=cursor,
                          filter={"property": "object", "value": "page"})
        for x in r.get("results", []):
            if x.get("object") != "page":
                continue
            props = x.get("properties", {})
            title = title_of(props) or "(untitled)"
            link = url_of(props, "Link") or x.get("url")
            # Brand-deals DB carries financials/PII. By default it is PRIVATE (business) and stays
            # OUT of the content brain entirely — set BRAIN_INCLUDE_BUSINESS=1 only to load it into
            # a full LOCAL vault (never into the hosted/cloud content brain).
            is_deal = len(DEAL_PROPS & set(props.keys())) >= 2
            if is_deal and not INCLUDE_BUSINESS:
                skipped_business += 1
                continue
            # explicit series label from the tracker — the source of truth for a named series.
            # Set a `Series` select in Notion, or name a boolean column via NOTION_SERIES_CHECKBOX.
            sv = sel(props, "Series")
            series = (sv.strip().lower().replace(" ", "_")[:20] if sv
                      else (SERIES_FROM_CHECKBOX if SERIES_CHECKBOX
                            and (props.get(SERIES_CHECKBOX) or {}).get("checkbox") else None))
            if is_deal:
                kind, sponsored, brand, visibility = "deal", 1, title, "business"
                stage, pay = sel(props, "Stage"), sel(props, "Payment Status")
                pub = date_of(props, *DEAL_DATE_PROPS)
                caption = f"Brand deal | brand: {title} | stage: {stage} | payment: {pay}"
                body = ""
            else:
                visibility = "content"
                typ, status, cat = sel(props, "Type"), sel(props, "Status"), sel(props, "Category")
                sponsored = 1 if ((typ and "Sponsor" in typ) or (cat and "Brand" in cat)) else 0
                brand = title if sponsored else None
                kind = "note"
                pub = date_of(props, "Publication Date", "Deadline")
                body = body_text(x["id"])
                caption = (f"Type: {typ} | Status: {status} | Category: {cat}"
                           + ("\n\n" + body if body else ""))[:4000]
            emb = (f"{title}. {caption}")[:3000]
            outid = cur.var(oracledb.NUMBER)
            cur.execute(
                """
                insert into posts (platform_id, kind, title, caption, url, published_at,
                                   sponsored, brand, visibility, series, content_embedding)
                values ('notion', :kind, :title, :caption, :url, :pub, :sp, :brand, :viz, :series,
                        vector_embedding(MINILM using :emb as data))
                returning post_id into :outid
                """,
                kind=kind, title=title[:1000], caption=caption, url=link, pub=iso(pub),
                sp=sponsored, brand=(brand[:200] if brand else None), viz=visibility,
                series=series, emb=emb, outid=outid,
            )
            post_id = int(outid.getvalue()[0])
            for i, ch in enumerate(chunks_of(body)):
                cur.execute(
                    """insert into content_chunks (post_id, seq, chunk, embedding)
                       values (:pid, :seq, :chunk, vector_embedding(MINILM using :emb as data))""",
                    pid=post_id, seq=i, chunk=ch, emb=ch[:3000],
                )
                total_chunks += 1
            n += 1
            if n % 25 == 0:
                print(f"  {n} pages, {total_chunks} chunks...")
        if not r.get("has_more"):
            break
        cursor = r.get("next_cursor")
    conn.commit()
    cur.execute("select count(*) from posts where platform_id='notion' and sponsored=1")
    sp = cur.fetchone()[0]
    print(f"loaded {n} Notion pages ({sp} sponsored) + {total_chunks} chunks into the brain"
          + (f"; skipped {skipped_business} private brand-deal rows (business)" if skipped_business else ""))
    conn.close()


if __name__ == "__main__":
    main()
