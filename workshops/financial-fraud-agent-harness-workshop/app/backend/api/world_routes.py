"""World Explorer endpoints — geographic features for the globe view.

The front-end's WorldExplorer renders four layers:
  - branches             (fixed dots at branch locations)
  - merchants            (dots at merchant locations)
  - suspicious_activity  (recent FLAGGED / BLOCKED transactions plotted at
                          their merchant location, sized by amount)
  - activity_arcs        (arcs from the transacting account's home branch to
                          the merchant, for flagged / blocked transactions)

Plus a search endpoint that resolves "Wall Street", "BitVault Exchange",
"Isabella Allen", "EUROPE" to a geographic anchor the front-end can fly the
camera to.

All queries respect the active identity (`as_user` query param) — if the user
acts as `analyst.east`, only EUROPE + MIDDLE_EAST branches, merchants, and
flagged transactions appear on the globe. Same identity contract as the data
explorer.
"""

from __future__ import annotations

import traceback

import oracledb
from flask import Blueprint, jsonify, request

from api.identities import get_identity
from config import DEMO_USER, WORLD_ARC_LIMIT


world_bp = Blueprint("world", __name__)
_state: dict = {}


def init_world_routes(*, agent_conn):
    _state["agent_conn"] = agent_conn


# Rough centroid coordinates for the four bank regions (used when no specific
# branch / merchant row is a better anchor).
REGION_CENTROIDS: dict[str, tuple[float, float]] = {
    "AMERICAS":     (38.0,  -98.0),
    "EUROPE":       (50.0,    8.0),
    "MIDDLE_EAST":  (27.0,   45.0),
    "ASIA_PACIFIC": (12.0,  105.0),
}


def _ident_region_filter(identity, alias: str = "v") -> tuple[str, dict]:
    """Return a SQL fragment + binds restricting rows by region for this
    identity. Empty when the identity has no region restriction.

    `alias` is the table alias the region column is qualified with in the
    caller's SQL (default 'v' — legacy alias kept for the arcs query).
    """
    if identity.regions is None:
        return "", {}
    marks = ",".join(f":r{i}" for i in range(len(identity.regions)))
    binds = {f"r{i}": r for i, r in enumerate(identity.regions)}
    return f" AND {alias}.region IN ({marks})", binds


@world_bp.route("/api/world", methods=["GET"])
def world():
    """Return all geo-features for the globe in one payload."""
    try:
        conn = _state.get("agent_conn")
        if not conn:
            return jsonify({"error": "not initialized"}), 503

        identity = get_identity(request.args.get("as_user"))
        region_clause, region_binds = _ident_region_filter(identity, alias="b")
        # Same region filter, qualified for the merchants query below (alias `m`).
        merchant_region_clause, _ = _ident_region_filter(identity, alias="m")
        # ...and for the merchant-summary rollup, which only joins transactions
        # + merchants and so must filter on the transaction's own region column.
        txn_region_clause, _ = _ident_region_filter(identity, alias="t")

        branches = []
        merchants = []
        suspicious = []
        arcs = []
        customers_forbidden = "FINANCE.CUSTOMERS" in identity.forbid_tables
        sar_forbidden = "FINANCE.SAR_REPORTS" in identity.forbid_tables
        merchant_summary: dict[str, int] = {}

        with conn.cursor() as cur:
            # Branches — every branch shows (region-filtered for analysts).
            cur.execute(
                f"SELECT branch_id, branch_code, name, city, country, region, "
                f"       latitude, longitude, opened_year "
                f"  FROM {DEMO_USER}.branches b "
                f" WHERE 1=1 {region_clause} "
                f" ORDER BY branch_id",
                region_binds,
            )
            for bid, code, name, city, country, region, lat, lon, year in cur:
                if lat is None or lon is None:
                    continue
                branches.append({
                    "kind": "branch",
                    "id": int(bid),
                    "branch_code": code,
                    "name": name,
                    "city": city,
                    "country": country,
                    "region": region,
                    "lat": float(lat),
                    "lng": float(lon),
                    "opened_year": int(year or 0),
                })

            # Merchants — region-filtered the same way.
            cur.execute(
                f"SELECT merchant_id, name, mcc_code, category, country, region, "
                f"       latitude, longitude "
                f"  FROM {DEMO_USER}.merchants m "
                f" WHERE 1=1 {merchant_region_clause} "
                f" ORDER BY merchant_id",
                region_binds,
            )
            for mid, name, mcc, cat, country, region, lat, lon in cur:
                if lat is None or lon is None:
                    continue
                merchants.append({
                    "kind": "merchant",
                    "id": int(mid),
                    "name": name,
                    "mcc_code": mcc,
                    "category": cat,
                    "country": country,
                    "region": region,
                    "lat": float(lat),
                    "lng": float(lon),
                })

            # Suspicious activity — recent FLAGGED / BLOCKED transactions,
            # sized by amount_cents. Merchant-located rules (GEO_VELOCITY,
            # HIGH_RISK_COUNTRY) plot at the merchant; the cash rules
            # (STRUCTURING, RAPID_CASH_OUT, LARGE_CASH_DEPOSIT) carry no
            # merchant_id, so they anchor at the account's home branch —
            # otherwise three of the five AML rules never reach the globe.
            # Ops viewer sees these (no customer PII needed); analysts see
            # only their regions' rows, which is why the branches join is
            # required (`region_clause` is qualified with `b.`).
            cur.execute(
                f"SELECT t.txn_id, t.txn_ts, t.amount_cents, t.status, "
                f"       t.flag_reason, t.channel, t.region, "
                f"       m.merchant_id, m.name AS merchant_name, m.category, "
                f"       m.latitude, m.longitude, "
                f"       b.latitude AS b_lat, b.longitude AS b_lng "
                f"  FROM {DEMO_USER}.transactions t "
                f"  JOIN {DEMO_USER}.accounts a ON a.account_id = t.account_id "
                f"  JOIN {DEMO_USER}.branches b ON b.branch_id = a.branch_id "
                f"  LEFT JOIN {DEMO_USER}.merchants m ON m.merchant_id = t.merchant_id "
                f" WHERE t.status IN ('FLAGGED', 'BLOCKED') "
                f"   AND t.txn_ts >= SYSTIMESTAMP - INTERVAL '120' DAY(3) "
                f" {region_clause} "
                f" ORDER BY t.txn_id ",
                region_binds,
            )
            for (tid, ts, amount, status, reason, channel, region,
                 mid, mname, mcat, mlat, mlon, blat, blng) in cur:
                # Merchant location when the rule has one, else the branch.
                lat = mlat if mlat is not None else blat
                lng = mlon if mlon is not None else blng
                if lat is None or lng is None:
                    continue
                jitter = (int(tid) * 0.0173) % 0.06 - 0.03
                suspicious.append({
                    "kind": "suspicious_activity",
                    "id": int(tid),
                    "txn_id": int(tid),
                    "txn_ts": str(ts) if ts else None,
                    "amount_cents": int(amount or 0),
                    "status": status,
                    "flag_reason": reason,
                    "channel": channel,
                    "region": region,
                    "merchant": mname,
                    "merchant_category": mcat,
                    "lat": float(lat) + jitter,
                    "lng": float(lng) + jitter,
                })

            # Activity arcs — home branch → merchant for flagged / blocked
            # transactions in the last 120 days. Capped to the most recent
            # WORLD_ARC_LIMIT rows: drawing every arc (hundreds) buries the
            # globe in lines. Recency, not txn_id, decides what's kept, so the
            # map always reflects the freshest activity.
            cur.execute(
                f"SELECT t.txn_id, t.status, t.flag_reason, t.region, "
                f"       b.branch_code, b.name AS branch_name, "
                f"       b.latitude AS b_lat, b.longitude AS b_lng, "
                f"       m.name AS merchant_name, "
                f"       m.latitude AS m_lat, m.longitude AS m_lng "
                f"  FROM {DEMO_USER}.transactions t "
                f"  JOIN {DEMO_USER}.accounts a ON a.account_id = t.account_id "
                f"  JOIN {DEMO_USER}.branches b ON b.branch_id = a.branch_id "
                f"  LEFT JOIN {DEMO_USER}.merchants m ON m.merchant_id = t.merchant_id "
                f" WHERE t.status IN ('FLAGGED', 'BLOCKED') "
                f"   AND t.txn_ts >= SYSTIMESTAMP - INTERVAL '120' DAY(3) "
                f"   AND m.latitude IS NOT NULL "
                f" {region_clause} "
                f" ORDER BY t.txn_ts DESC, t.txn_id DESC "
                f" FETCH FIRST :arc_limit ROWS ONLY",
                {**region_binds, "arc_limit": WORLD_ARC_LIMIT},
            )
            for (tid, status, reason, region, bcode, bname,
                 blat, blng, mname, mlat, mlng) in cur:
                if blat is None or mlat is None:
                    continue
                arcs.append({
                    "kind": "activity_arc",
                    "id": int(tid),
                    "status": status,
                    "flag_reason": reason,
                    "region": region,
                    "branch": bname,
                    "branch_code": bcode,
                    "merchant": mname,
                    "origin": {"lat": float(blat), "lng": float(blng)},
                    "destination": {"lat": float(mlat), "lng": float(mlng)},
                })

            # Merchant summary — flagged transactions per merchant.
            cur.execute(
                f"SELECT m.name, COUNT(*) "
                f"  FROM {DEMO_USER}.transactions t "
                f"  JOIN {DEMO_USER}.merchants m ON m.merchant_id = t.merchant_id "
                f" WHERE t.status IN ('FLAGGED', 'BLOCKED') "
                f" {txn_region_clause} "
                f" GROUP BY m.name ORDER BY 2 DESC",
                region_binds,
            )
            for mname, n in cur:
                merchant_summary[mname] = int(n or 0)

        return jsonify({
            "identity": identity.as_json(),
            "branches": branches,
            "merchants": merchants,
            "suspicious_activity": suspicious,
            "activity_arcs": arcs,
            "customers_forbidden": customers_forbidden,
            "sar_forbidden": sar_forbidden,
            "merchant_summary": merchant_summary,
            "stats": {
                "branches": len(branches),
                "merchants": len(merchants),
                "suspicious_activity": len(suspicious),
                "activity_arcs": len(arcs),
            },
        })
    except oracledb.DatabaseError as e:
        traceback.print_exc()
        return jsonify({"error": f"OracleError: {e}"}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"{type(e).__name__}: {e}"}), 500


@world_bp.route("/api/world/search", methods=["GET"])
def search():
    """Resolve a free-text query to a geographic anchor on the globe.

    Looks at branch codes/names/cities, merchant names/categories, customer
    names, and region labels in priority order. Returns the first match with
    lat/lng so the front-end can fly the camera. Empty matches return 404
    with a clear error.
    """
    try:
        conn = _state.get("agent_conn")
        if not conn:
            return jsonify({"error": "not initialized"}), 503

        q = (request.args.get("q") or "").strip()
        if not q:
            return jsonify({"error": "missing q"}), 400
        identity = get_identity(request.args.get("as_user"))
        needle = f"%{q.lower()}%"

        # 0. Region label — exact match on the four bank regions.
        region_key = q.strip().upper().replace(" ", "_")
        if region_key in REGION_CENTROIDS:
            lat, lng = REGION_CENTROIDS[region_key]
            return jsonify({
                "kind": "region",
                "id": region_key,
                "name": region_key,
                "region": region_key,
                "lat": lat,
                "lng": lng,
            })

        # 1. Branch code (exact-ish) or name/city match. Region-filtered like
        #    /api/world, otherwise a regional analyst could fly the camera to a
        #    branch their persona is meant never to see. The OR group must stay
        #    parenthesised so the region predicate applies to every disjunct.
        branch_region_clause, branch_region_binds = _ident_region_filter(identity, alias="b")
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT branch_id, branch_code, name, city, country, region, "
                f"       latitude, longitude "
                f"  FROM {DEMO_USER}.branches b "
                f" WHERE (LOWER(branch_code) = :exact OR LOWER(name) LIKE :needle "
                f"    OR LOWER(city) LIKE :needle) "
                f" {branch_region_clause} "
                f" ORDER BY CASE WHEN LOWER(branch_code) = :exact THEN 0 ELSE 1 END "
                f" FETCH FIRST 1 ROWS ONLY",
                exact=q.lower(), needle=needle, **branch_region_binds,
            )
            row = cur.fetchone()
            if row:
                bid, code, name, city, country, region, lat, lng = row
                return jsonify({
                    "kind": "branch",
                    "id": int(bid),
                    "name": name,
                    "branch_code": code,
                    "city": city,
                    "country": country,
                    "region": region,
                    "lat": float(lat),
                    "lng": float(lng),
                })

        # 2. Merchant name / category.
        region_clause, region_binds = _ident_region_filter(identity, alias="m")
        with conn.cursor() as cur:
            sql = (
                f"SELECT merchant_id, name, category, country, region, "
                f"       latitude, longitude "
                f"  FROM {DEMO_USER}.merchants m "
                f" WHERE (LOWER(m.name) LIKE :needle OR LOWER(m.category) LIKE :needle) "
                f" {region_clause} "
                f" FETCH FIRST 1 ROWS ONLY"
            )
            cur.execute(sql, {"needle": needle, **region_binds})
            row = cur.fetchone()
            if row:
                mid, name, cat, country, region, lat, lng = row
                return jsonify({
                    "kind": "merchant",
                    "id": int(mid),
                    "name": name,
                    "category": cat,
                    "country": country,
                    "region": region,
                    "lat": float(lat),
                    "lng": float(lng),
                })

        # 3. Customer name — anchored at their primary (oldest) account's
        #    branch. Respects identity region + table forbids.
        if "FINANCE.CUSTOMERS" not in identity.forbid_tables:
            region_clause_c, region_binds_c = _ident_region_filter(identity, alias="b")
            with conn.cursor() as cur:
                sql = (
                    f"SELECT cu.customer_id, cu.full_name, b.name, b.city, b.region, "
                    f"       b.latitude, b.longitude "
                    f"  FROM {DEMO_USER}.customers cu "
                    f"  JOIN {DEMO_USER}.accounts a ON a.customer_id = cu.customer_id "
                    f"  JOIN {DEMO_USER}.branches b ON b.branch_id = a.branch_id "
                    f" WHERE LOWER(cu.full_name) LIKE :needle "
                    f" {region_clause_c} "
                    f" ORDER BY a.opened_ts "
                    f" FETCH FIRST 1 ROWS ONLY"
                )
                cur.execute(sql, {"needle": needle, **region_binds_c})
                row = cur.fetchone()
                if row:
                    cid, full_name, bname, city, region, lat, lng = row
                    return jsonify({
                        "kind": "customer",
                        "id": int(cid),
                        "name": full_name,
                        "branch": bname,
                        "city": city,
                        "region": region,
                        "lat": float(lat),
                        "lng": float(lng),
                    })

        return jsonify({"error": f"no match for {q!r}"}), 404
    except oracledb.DatabaseError as e:
        traceback.print_exc()
        return jsonify({"error": f"OracleError: {e}"}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"{type(e).__name__}: {e}"}), 500


@world_bp.errorhandler(Exception)
def _handle_blueprint_errors(e):
    traceback.print_exc()
    return jsonify({"error": f"{type(e).__name__}: {e}"}), 500
