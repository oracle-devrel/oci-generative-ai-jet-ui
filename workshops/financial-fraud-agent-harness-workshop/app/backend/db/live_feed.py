"""Live transaction feed — a bounded simulator that streams new banking
activity into FINANCE so the app feels like a production system under real-time
load.

Transaction arrivals follow a Poisson process whose mean gap tracks the hour
of day (quiet overnight, busy mid-morning), with occasional bursts — so the
feed reads like a real bank rather than a metronome. Whenever a flagged event
rolls the spotlight share it replays a case the autonomous triage actually
captured, which keeps the globe and the AML panel telling the same story. Each
event is inserted into FINANCE and broadcast over Socket.IO as `live_txn`: the
World panel pulses a marker at the transaction's merchant/branch, draws an arc
from the account's home branch, and ticks a live counter — so the globe keeps
moving even when the user isn't asking a question.

Design notes
------------
* Writes go through the FINANCE (demo) user. AGENT only holds SELECT ANY TABLE,
  and the DBMS_RLS policies on the FINANCE tables are SELECT-only, so INSERTs
  are unaffected by them.
* Live rows use a reserved high `txn_id` range (>= LIVE_BASE) so they can be
  purged without ever touching the curated seed data. A per-tick cap + TTL keep
  the overlay bounded and self-cleaning.
* Reads stay identity-gated: the globe still fetches /api/world as the acting
  persona, and the client drops live events outside that persona's regions, so
  an analyst.east client never plots an AMERICAS transaction.
* Toggleable at runtime via the Socket.IO `live_feed_control` event; disable
  entirely with LIVE_FEED=false.
"""

from __future__ import annotations

import math
import random
import time
from datetime import datetime, timezone

from flask import request as flask_request

from agent.aml_capture import spotlight_profiles
from config import (
    DEMO_USER,
    LIVE_FEED,
    LIVE_FEED_BURST,
    LIVE_FEED_FLAG_RATE,
    LIVE_FEED_INTERVAL,
    LIVE_FEED_MAX,
    LIVE_FEED_SPOTLIGHT,
    LIVE_FEED_TTL_MIN,
)
from db.connection import connect_demo


# Reserved txn_id range for simulated rows (the seed tops out in the low
# thousands), so purging can never touch curated data.
LIVE_BASE = 9_000_000

# Relative arrival rate per UTC hour (index = hour): quiet overnight, peaking
# mid-morning to early afternoon. Weekends scale the whole curve down by 0.7.
DIURNAL = [
    0.25, 0.20, 0.20, 0.20, 0.25, 0.40, 0.70, 1.00, 1.30, 1.50, 1.60, 1.60,
    1.50, 1.50, 1.45, 1.40, 1.30, 1.10, 0.90, 0.75, 0.60, 0.50, 0.40, 0.30,
]

# (reason, weight, merchant_located). The merchant-located rules plot at a
# merchant (GEO_VELOCITY crosses borders); the cash rules carry no merchant and
# anchor at the account's home branch — matching the world route's logic.
_FLAG_RULES = [
    ("STRUCTURING",        40, False),
    ("RAPID_CASH_OUT",     20, False),
    ("HIGH_RISK_COUNTRY",  15, True),
    ("GEO_VELOCITY",       15, True),
    ("LARGE_CASH_DEPOSIT", 10, False),
]
_CHANNELS = ["ATM", "POS", "ONLINE", "WIRE", "MOBILE"]
_TYPES = ["PURCHASE", "WITHDRAWAL", "DEPOSIT", "TRANSFER"]

_state: dict = {
    "socketio": None,
    "enabled": bool(LIVE_FEED),
    "interval": float(LIVE_FEED_INTERVAL),
    "conn": None,
    "dimensions": None,
    "emitted": 0,
    "seq": 0,
    # Arrival cadence: bursts still to fire, and when the next event is due
    # (monotonic clock) so status_payload can expose an ETA to the header.
    "burst_left": 0,
    "next_at": None,
}


# --------------------------------------------------------------------------- #
# Connection + dimension cache
# --------------------------------------------------------------------------- #

def _conn():
    c = _state.get("conn")
    if c is None:
        c = connect_demo()
        _state["conn"] = c
    return c


def _reset_conn():
    c = _state.get("conn")
    if c is not None:
        try:
            c.close()
        except Exception:
            pass
    _state["conn"] = None


def _load_dimensions(conn) -> dict:
    """Cache the accounts (with their branch + region + lat/lng) and merchants
    so each tick only has to INSERT."""
    accounts: list[dict] = []
    merchants: list[dict] = []
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT a.account_id, a.customer_id, b.branch_id, b.branch_code, b.name, b.city, "
            f"       b.region, b.latitude, b.longitude "
            f"  FROM {DEMO_USER}.accounts a "
            f"  JOIN {DEMO_USER}.branches b ON b.branch_id = a.branch_id"
        )
        for aid, cid, bid, code, name, city, region, lat, lng in cur:
            if lat is None or lng is None:
                continue
            accounts.append({
                "account_id": int(aid), "customer_id": int(cid), "branch_id": int(bid),
                "branch_code": code, "branch": name, "city": city,
                "region": region, "lat": float(lat), "lng": float(lng),
            })
        cur.execute(
            f"SELECT merchant_id, name, category, region, latitude, longitude "
            f"  FROM {DEMO_USER}.merchants"
        )
        for mid, name, cat, region, lat, lng in cur:
            if lat is None or lng is None:
                continue
            merchants.append({
                "merchant_id": int(mid), "name": name, "category": cat,
                "region": region, "lat": float(lat), "lng": float(lng),
            })

    by_region: dict[str, list[dict]] = {}
    for m in merchants:
        by_region.setdefault(m["region"], []).append(m)
    return {"accounts": accounts, "merchants": merchants, "by_region": by_region}


# --------------------------------------------------------------------------- #
# Picking a plausible event
# --------------------------------------------------------------------------- #

def _weighted_rule():
    total = sum(w for _, w, _ in _FLAG_RULES)
    r = random.uniform(0, total)
    acc = 0.0
    for reason, w, merchant_located in _FLAG_RULES:
        acc += w
        if r <= acc:
            return reason, merchant_located
    return _FLAG_RULES[0][0], _FLAG_RULES[0][2]


def _pick_merchant(dims, region, cross_border=False):
    if cross_border:
        pool = [m for m in dims["merchants"] if m["region"] != region] or dims["merchants"]
    else:
        pool = dims["by_region"].get(region) or dims["merchants"]
    return random.choice(pool) if pool else None


def _amount(status: str) -> int:
    if status == "COMPLETED":
        return random.randint(5_00, 250_00)  # $5–$250
    # AML hits skew large — that's what makes them worth flagging.
    return random.choice([
        random.randint(900_00, 5_000_00),       # $900–$5k
        random.randint(10_000_00, 50_000_00),   # $10k–$50k
    ])


# --------------------------------------------------------------------------- #
# Insert + purge
# --------------------------------------------------------------------------- #

def _next_txn_id(cur) -> int:
    cur.execute(
        f"SELECT NVL(MAX(txn_id), :b - 1) + 1 FROM {DEMO_USER}.transactions "
        f" WHERE txn_id >= :b",
        b=LIVE_BASE,
    )
    return int(cur.fetchone()[0])


def _purge(cur) -> None:
    """Drop live rows past their TTL, then trim to the cap. Curated seed rows
    (txn_id < LIVE_BASE) are never touched."""
    cur.execute(
        f"DELETE FROM {DEMO_USER}.transactions "
        f" WHERE txn_id >= :b "
        f"   AND txn_ts < SYSTIMESTAMP - NUMTODSINTERVAL(:m, 'MINUTE')",
        b=LIVE_BASE, m=LIVE_FEED_TTL_MIN,
    )
    cur.execute(
        f"SELECT COUNT(*) FROM {DEMO_USER}.transactions WHERE txn_id >= :b",
        b=LIVE_BASE,
    )
    n = int(cur.fetchone()[0])
    if n >= LIVE_FEED_MAX:
        over = n - LIVE_FEED_MAX + 1
        cur.execute(
            f"DELETE FROM {DEMO_USER}.transactions WHERE txn_id IN ("
            f"  SELECT txn_id FROM {DEMO_USER}.transactions "
            f"   WHERE txn_id >= :b ORDER BY txn_ts FETCH FIRST :k ROWS ONLY)",
            b=LIVE_BASE, k=over,
        )


def _emit_one() -> dict | None:
    dims = _state.get("dimensions")
    if not dims:
        dims = _load_dimensions(_conn())
        _state["dimensions"] = dims
    if not dims["accounts"]:
        return None

    acct = random.choice(dims["accounts"])
    flagged = random.random() < LIVE_FEED_FLAG_RATE
    amount = None  # the spotlight path sizes its own replay

    # Spotlight: replay a case the autonomous triage actually captured, so the
    # world feed and the AML panel tell the same story.
    profile = None
    if flagged and random.random() < LIVE_FEED_SPOTLIGHT:
        profiles = spotlight_profiles()
        profile = random.choice(profiles) if profiles else None
        if profile is not None:
            pool = [a for a in dims["accounts"] if a["customer_id"] == int(profile["customer_id"])]
            if pool:
                acct = random.choice(pool)
            else:
                profile = None  # no account loaded for that customer — generate one instead

    if profile is not None:
        reason = profile["typology"]
        status = "BLOCKED" if random.random() < float(profile["blocked_share"]) else "FLAGGED"
        # GEO_VELOCITY is the cross-border typology — send it abroad.
        merchant = (
            _pick_merchant(dims, acct["region"], cross_border=(reason == "GEO_VELOCITY"))
            if profile["merchant_located"] else None
        )
        # Size the replay like the case's own average flagged txn, ±25%.
        base = int(profile["exposure_cents"]) // max(1, int(profile["flagged_txns"]))
        amount = max(900_00, int(base * random.uniform(0.75, 1.25)))
    elif flagged:
        reason, merchant_located = _weighted_rule()
        status = "BLOCKED" if random.random() < 0.2 else "FLAGGED"
        # GEO_VELOCITY is the cross-border typology — send it abroad.
        merchant = (
            _pick_merchant(dims, acct["region"], cross_border=(reason == "GEO_VELOCITY"))
            if merchant_located else None
        )
    else:
        status, reason = "COMPLETED", None
        merchant = _pick_merchant(dims, acct["region"])

    if amount is None:
        amount = _amount(status)
    channel = random.choice(_CHANNELS)
    txn_type = random.choice(_TYPES)

    if merchant:
        lat, lng, mid = merchant["lat"], merchant["lng"], merchant["merchant_id"]
    else:
        lat, lng, mid = acct["lat"], acct["lng"], None

    ts = datetime.now(timezone.utc)
    conn = _conn()
    cur = conn.cursor()
    try:
        tid = _next_txn_id(cur)
        cur.execute(
            f"INSERT INTO {DEMO_USER}.transactions "
            f" (txn_id, account_id, merchant_id, txn_ts, amount_cents, currency, "
            f"  channel, txn_type, status, flag_reason, region) "
            f" VALUES (:1, :2, :3, SYSTIMESTAMP, :4, 'USD', :5, :6, :7, :8, :9)",
            [tid, acct["account_id"], mid, amount, channel, txn_type,
             status, reason, acct["region"]],
        )
        _purge(cur)
        conn.commit()
    finally:
        cur.close()

    _state["seq"] += 1
    return {
        "seq": _state["seq"],
        "txn_id": tid,
        "txn_ts": ts.isoformat(),
        "amount_cents": amount,
        "currency": "USD",
        "channel": channel,
        "txn_type": txn_type,
        "status": status,
        "flag_reason": reason,
        "region": acct["region"],
        "account_id": acct["account_id"],
        "merchant_id": mid,
        "merchant": merchant["name"] if merchant else None,
        "merchant_category": merchant["category"] if merchant else None,
        "lat": lat,
        "lng": lng,
        "origin": {
            "lat": acct["lat"], "lng": acct["lng"],
            "branch": acct["branch"], "branch_code": acct["branch_code"],
        },
    }


# --------------------------------------------------------------------------- #
# Arrival cadence
# --------------------------------------------------------------------------- #

def _next_gap_seconds(now_utc: datetime | None = None) -> float:
    """Seconds until the next event — a diurnal Poisson arrival process.

    `LIVE_FEED_INTERVAL` is the *peak-hour* mean gap; the DIURNAL table scales
    it by the hour of day (weekends run ~30% lighter). Poisson spacing makes
    quiet stretches and quick clusters both possible, and a burst in progress
    wins outright — that is what a real bank feed looks like.
    """
    if _state["burst_left"] > 0:
        _state["burst_left"] -= 1
        return random.uniform(0.8, 2.4)

    now = now_utc or datetime.now(timezone.utc)
    mult = DIURNAL[now.hour] * (0.7 if now.weekday() >= 5 else 1.0)
    gap = -math.log(1.0 - random.random()) * _state["interval"] / mult
    return min(max(gap, 0.8), 150.0)


# --------------------------------------------------------------------------- #
# Loop + status + socket wiring
# --------------------------------------------------------------------------- #

def _loop(socketio) -> None:
    socketio.sleep(4)  # let boot finish before the first event
    while True:
        try:
            if _state["enabled"]:
                payload = _emit_one()
                if payload:
                    _state["emitted"] += 1
                    socketio.emit("live_txn", payload)
                    # Arrivals clump: a hit occasionally opens a short burst.
                    if random.random() < LIVE_FEED_BURST:
                        _state["burst_left"] = random.randint(3, 5)
        except Exception as e:
            print(f"[live_feed] tick failed: {type(e).__name__}: {e}")
            _reset_conn()
        gap = _next_gap_seconds()
        _state["next_at"] = time.monotonic() + gap
        socketio.sleep(gap)


def status_payload() -> dict:
    next_at = _state["next_at"]
    return {
        "enabled": bool(_state["enabled"]),
        "interval": _state["interval"],
        "mean_s": _state["interval"],
        "spotlight_share": LIVE_FEED_SPOTLIGHT,
        "burst_left": _state["burst_left"],
        "next_in_ms": (
            max(0, round((next_at - time.monotonic()) * 1000))
            if _state["enabled"] and next_at else None
        ),
        "emitted": _state["emitted"],
        "max": LIVE_FEED_MAX,
        "ttl_min": LIVE_FEED_TTL_MIN,
        "flag_rate": LIVE_FEED_FLAG_RATE,
    }


def set_enabled(value) -> dict:
    _state["enabled"] = bool(value)
    return status_payload()


def init_live_feed(*, socketio) -> None:
    """Register the control events and start the background feed."""
    _state["socketio"] = socketio

    @socketio.on("live_feed_status_request")
    def _on_status():
        socketio.emit("live_feed_status", status_payload(), room=flask_request.sid)

    @socketio.on("live_feed_control")
    def _on_control(data):
        set_enabled((data or {}).get("enabled"))
        socketio.emit("live_feed_status", status_payload())

    if _state["enabled"]:
        socketio.start_background_task(_loop, socketio)
        print(f"  Live feed: ON (mean {_state['interval']:g}s at peak · diurnal · "
              f"spotlight {LIVE_FEED_SPOTLIGHT:.0%} · max {LIVE_FEED_MAX} rows · "
              f"ttl {LIVE_FEED_TTL_MIN}m · flag rate {LIVE_FEED_FLAG_RATE:.0%})")
    else:
        print("  Live feed: OFF (set LIVE_FEED=true to enable).")
