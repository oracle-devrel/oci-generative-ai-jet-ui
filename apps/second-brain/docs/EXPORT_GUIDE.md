# Data Export Guide

For **your own** content, official exports beat scraping: they're legal, complete (media +
metrics), and don't break when a platform changes its HTML. Trigger them in this order — the
slow ones first. Drop the downloaded bundles in an `exports/` folder (gitignored); the
normalizer scripts will read from there into `sources/`.

> **Start Instagram now.** Meta can take a few hours (sometimes longer). Everything else can be
> requested while it processes.

---

## 1. Instagram  *(primary — you crosspost from here)*

**Recommended: the API (auto-syncs new posts + performance).** For a **Creator/Business** account,
the *Instagram API with Instagram Login* pulls your media and engagement/reach on a schedule — **no
Facebook Page required, no scraping**. One-time setup:

1. **developers.facebook.com → Create app → type "Business".**
2. In the app: **Add product → Instagram → "API setup with Instagram login".**
3. **Generate access token →** connect your Creator account, grant **`instagram_business_basic`** +
   **`instagram_business_manage_insights`**. Copy the (short-lived) token shown.
4. In **App settings → Basic**, copy the **App secret**.
5. Mint a long-lived (~60-day) token:
   ```bash
   IG_APP_SECRET=<app secret> ./.venv/bin/python scripts/instagram_token.py <short-lived token>
   ```
   Paste the printed `IG_ACCESS_TOKEN=...` into `oracle/.env` (it's a **secret** — keep it out of git).
6. Load it (incremental — only adds new media each run):
   ```bash
   ./.venv/bin/python scripts/instagram.py
   ```
   Refresh the token every ~60 days with `scripts/instagram_token.py --refresh` (set a reminder —
   the scheduled sync pulls new posts but does **not** refresh the token).

**Alternative: one-time export** (good for a full historical backfill):
Instagram → **Profile → ☰ → Accounts Center → Your information and permissions → Download your
information**. Pick *Posts, Reels, Stories, Comments, Profile*, **Format: JSON**, **All time**,
download to device. ➡ Save the `.zip` to `exports/instagram/`.

## 2. LinkedIn

LinkedIn's official data archive is unreliable for post content: rich-media posts (video
especially) often arrive without their caption text. The dependable path is harvesting your own
activity feed from a logged-in browser session — your posts are all there, with full text.

1. Log in and open `linkedin.com/in/<you>/recent-activity/all/`.
2. Scroll to the bottom of your history, collecting each post's URN, author, text, relative age,
   and media type. An AI browser assistant can do the scrolling and collecting for you (keep it
   supervised — it's your logged-in session); the target JSON shape is documented in
   `scripts/linkedin_harvest.py`:

   ```json
   {"harvested_at": "...", "items": [
     {"urn": "urn:li:activity:...", "actor": "Your Name", "header": "",
      "text": "full post text", "rel": "3yr", "media": "video"}]}
   ```

3. Save as `linkedin_harvest.json` and load it — only your original posts are kept (set `LINKEDIN_ACTOR` to your display name; reposts of
   other people's content are filtered by the `actor` field), and reruns are dedupe-safe:

   ```bash
   ./.venv/bin/python scripts/linkedin_harvest.py ~/Downloads/linkedin_harvest.json
   ```

Relative ages ("3yr") become approximate dates — good enough for search and voice mining.
*(Optional: request the official archive too — **Settings & Privacy → Data Privacy → Get a copy
of your data → larger archive** — and if its `Shares.csv` has usable text for your posts, its
exact dates can complement the harvest.)*

## 3. TikTok

1. **Profile → ☰ → Settings and privacy → Account → Download your data**.
2. **Request data** · **File format: JSON** (not TXT).
3. When ready (under *Download data* tab), download the `.zip`.

➡ Save to `exports/tiktok/`. *(No loader ships for TikTok yet — copy any `scripts/` loader as a
template; the target is always the same `posts` contract.)*

## 4. YouTube

1. Go to **takeout.google.com**.
2. Deselect all → select **YouTube and YouTube Music**.
3. **All YouTube data included** → keep *videos* + *metadata* (history optional).
4. Export → choose `.zip`, one-time. Email when ready.

➡ Save to `exports/youtube/`. *(Note: `scripts/youtube.py` reads **yt-dlp** `.jsonl` output — see the
tutorial — not the Takeout format. Takeout is still worth keeping as your own full backup.)*

## 5. X / Twitter

1. **Settings → Your account → Download an archive of your data**.
2. Verify identity → **Request archive**. Can take up to **24 hours**.
3. Download when the email arrives.

➡ Save to `exports/twitter/`. (Archive is HTML/JS + a `data/` folder of JSON.) *(No loader ships for
X yet — copy any `scripts/` loader as a template.)*

Two archive caveats worth knowing before you trust it: retweets are stored truncated
(`RT @… ` + the first ~140 chars — other people's text, not yours, so usually fine) and all
links are `t.co`-shortened. On load, verify the archive's post count against the count your
profile displays — treat the archive as *claimed complete, verified on load*.

## 6. Threads

Threads has no export of its own — your Threads posts ride along in the **Instagram** export:
Accounts Center → **Download your information** → make sure **Threads** is among the selected
profiles, **Format: JSON**, **All time**. (The same request can cover Instagram — one bundle,
two platforms.)

➡ Save to `exports/threads/` (or point at the combined bundle). *(No loader ships for Threads
yet — copy any `scripts/` loader as a template.)*

---

## After exports land

Run the matching loader (`scripts/<platform>.py`) for each bundle — and for platforms without one,
**copy an existing loader as a template**: they all end at the same contract (map the export's
fields to `title`, `caption`, `url`, `published_at`, insert into `posts`; the embedding is
generated in-DB). Then run `classify_private.py` and `sync.py` to fold the new content in.

## What about content you can't export?

If something only exists live (e.g. a repost you don't own), prefer each platform's **official API**
over scraping — logins + anti-bot + terms of service make scraping an account risk.


## Obsidian (or any markdown folder)

No export needed — a vault is already plain files on disk. (Starting fresh?
Copy **[examples/obsidian-starter/](../examples/obsidian-starter/)** — a minimal
template with the frontmatter conventions pre-documented.) Set
`OBSIDIAN_VAULT=/path/to/vault` in `oracle/.env` and either run
`./.venv/bin/python scripts/obsidian.py` or let the daily sync pick it up.
Optional frontmatter per note: `title`, `tags`, `series`, `created`, and
`visibility` (anything other than `content` keeps that note out of the
searchable brain). Wikilinks are flattened to plain text. Edited notes
re-import in place; unchanged notes are skipped. **PDFs and EPUBs in the vault
are ingested too** — full text, chunked, as `kind='reference'`: searchable when
you ask, but excluded from the wiki compiler (your wiki synthesizes your work,
not your library). This also works for any folder that isn't Obsidian: a drop
folder of e-books, course notes, plain-text files.


## Substack

No export needed — your publication's public archive is served by Substack's own JSON API
(the same data the web archive page and RSS readers use; your content, no login, no
scraping). Set `SUBSTACK_URL=https://<you>.substack.com` in `oracle/.env` (a public URL,
not a secret) and either run `./.venv/bin/python scripts/substack.py` or let the daily
sync pick it up. Posts load as `kind='article'` (podcast posts as `'episode'`), full body
chunked for search; paid posts whose body isn't publicly served still land as a
title/subtitle row. Reloads are full-replace in one transaction, so reruns are safe.


## Google Drive

Connect specific Drive folders to your brain — Google Docs become searchable
notes, PDFs/EPUBs become searchable reference material, and your videos/photos
are never touched. No export step: the daily sync pulls changes via the API.

**The security model, up front:** the loader authenticates as its own *service
account* — a robot Google identity that starts with access to nothing. It can
only ever read the folders you explicitly share with it. Your wider Drive is
invisible to it by construction, not by promise.

### One-time setup (~10 minutes)

**1. Create a Google Cloud project.**
Go to [console.cloud.google.com](https://console.cloud.google.com) → project
picker (top bar) → **New project** → name it anything (e.g. `second-brain`) →
Create. Make sure the picker now shows the new project. (Reusing an existing
project also works — the project is just a container.)

**2. Enable the Drive API.**
Top search bar → "**Google Drive API**" → open it → **Enable**.

**3. Create a service account.**
Search "**Service accounts**" → **+ Create service account** → name it (e.g.
`brain-loader`) → Create and continue → skip the optional role steps
(Continue → Done). It needs **no** project roles: its only access will come
from Drive sharing.

**4. Download its key.**
Click the new service account → **Keys** tab → **Add key → Create new key →
JSON** → Create. A `.json` file downloads. Move it somewhere safe **outside
the repo** (e.g. `~/keys/brain-gdrive.json`) — this file is a credential;
treat it like a password and never commit it.

**5. Share folders with the service account.**
On the service account's page, copy its email
(`brain-loader@<project-id>.iam.gserviceaccount.com`). In Google Drive,
for each folder you want ingested: right-click → **Share** → paste that
email → **Viewer** → Share. (A warning about sharing outside your
organization is expected.)

**6. Configure the env.** In `oracle/.env`:

```bash
GDRIVE_KEY=/absolute/path/to/brain-gdrive.json
GDRIVE_FOLDERS=<folderId>,<folderId>    # each folder's URL ends in /folders/<id>
GDRIVE_EXCLUDE=<folderId>               # optional — see below
```

**7. Run it** (afterwards the daily sync runs it for you):

```bash
./.venv/bin/python scripts/gdrive.py
# -> gdrive: 12 new, 0 updated, 0 unchanged, 97 skipped (folders/media/oversize)
```

✅ **Checkpoint** — ask your brain about something that lives in a Drive doc:

```bash
./.venv/bin/python -c "import sys; sys.path.insert(0,'oracle/agent'); import db, content; \
  [print(f\"{r['dist']:.3f}  {r['title']}\") for r in \
   content.search_content(db.connect(), 'a phrase from one of your docs', k=3)]"
```

### What gets ingested (and what never does)

| In your folders | Becomes |
|---|---|
| Google Docs | searchable **notes** (exported as text) |
| `.md` / `.txt` | searchable **notes** |
| PDFs / EPUBs | full-text **reference** material — searchable when you ask, **excluded from the wiki compiler** (your wiki synthesizes your work, not your library) |
| video, audio, images, Sheets, Slides | **skipped by design** — footage stays footage |
| anything over 30 MB | skipped |

Each top-level shared folder's name becomes the `series`, so "list everything
in my course-library series" works from any AI client.

### Keep business subtrees out: `GDRIVE_EXCLUDE`

Real Drive folders mix content with things that must never enter a searchable
brain — contracts, agreements, financials. If a folder you want is the parent
of one you don't (say, `Projects/` contains `Projects/Contracts/`), don't
fork your folder structure: share the parent and put the sensitive subtree's
folder id in `GDRIVE_EXCLUDE`. The loader skips that whole branch.

Two patterns for sensitive-but-useful material:
- **Never ingest, read on demand**: keep it excluded; when an AI session needs
  one document as context, fetch it in the chat (via a Drive connector) and
  let it stay there. Context, not storage.
- **Decide first, then ingest**: the same classify-before-you-ingest rule as
  every other source (Lab 4). When in doubt, share a clean subfolder instead
  of a parent.



## ChatGPT / Claude (chat exports)

Both apps export your full chat history as a zip; neither has a push API.

- **ChatGPT**: Settings → **Data controls** → **Export data** → confirm — a
  download link arrives by email.
- **Claude**: Settings → **Privacy** → **Export data** — a download link
  arrives by email.

You don't even need to unzip: **drop the zip in the watch folder**
(`~/Downloads` by default; `EXPORT_WATCH_DIR` to change) and the next
`sync.py` run ingests it, re-runs the privacy classifier, and refreshes the
wiki. Set a monthly reminder — that's the one manual step chat sources need.
