"""World Explorer endpoints — geographic features for the globe view.

The front-end's WorldExplorer renders three layers:
  - ports        (fixed dots on coastlines)
  - vessels      (current AIS-style positions, animated by speed_knots)
  - voyages      (great-circle arcs from origin port to destination port)
  - carriers     (HQ countries, aggregated; no precise lat/long, geocoded by
                  centroid below for the demo)

Plus a search endpoint that resolves "Maersk", "MSC OSCAR", "SGSIN", "Singapore"
to a geographic anchor the front-end can fly the camera to.

All queries respect the active identity (`as_user` query param) — if the user
acts as `analyst.east`, only ATLANTIC + MEDITERRANEAN voyages and the vessels
on them appear on the globe. Same identity contract as the data explorer.
"""

from __future__ import annotations

import traceback

import oracledb
from flask import Blueprint, jsonify, request

from api.identities import get_identity
from config import DEMO_USER


world_bp = Blueprint("world", __name__)
_state: dict = {}


def init_world_routes(*, agent_conn):
    _state["agent_conn"] = agent_conn


# Rough centroid coordinates for the carriers' HQ countries. Real geocoding
# would tie to ISO-3166; this is enough for the demo's globe markers.
COUNTRY_CENTROIDS: dict[str, tuple[float, float]] = {
    "Denmark":      (56.0,   10.0),
    "Switzerland":  (46.8,    8.2),
    "France":       (46.6,    2.2),
    "China":        (35.0,  103.8),
    "Germany":      (51.1,   10.4),
    "Japan":        (36.2,  138.2),
    "Taiwan":       (23.7,  121.0),
    "South Korea":  (35.9,  127.7),
    "Israel":       (31.0,   34.8),
    "Hong Kong":    (22.3,  114.2),
    "Singapore":    ( 1.35, 103.8),
    "USA":          (39.8,  -98.6),
    "Australia":    (-25.3, 133.8),
}


def _ident_region_filter(identity) -> tuple[str, dict]:
    """Return a SQL fragment + binds restricting voyages by ocean_region for
    this identity. Empty when the identity has no region restriction."""
    if identity.regions is None:
        return "", {}
    marks = ",".join(f":r{i}" for i in range(len(identity.regions)))
    binds = {f"r{i}": r for i, r in enumerate(identity.regions)}
    return f" AND v.ocean_region IN ({marks})", binds


@world_bp.route("/api/world", methods=["GET"])
def world():
    """Return all geo-features for the globe in one payload."""
    try:
        conn = _state.get("agent_conn")
        if not conn:
            return jsonify({"error": "not initialized"}), 503

        identity = get_identity(request.args.get("as_user"))
        region_clause, region_binds = _ident_region_filter(identity)

        ports = []
        vessels = []
        voyages = []
        carriers = []
        containers = []
        carrier_summary: dict[str, int] = {}
        containers_forbidden = "SUPPLYCHAIN.CONTAINERS" in identity.forbid_tables

        with conn.cursor() as cur:
            # Ports — every port shows. Ports aren't region-restricted.
            cur.execute(
                f"SELECT port_code, name, country, ocean_region, latitude, longitude, "
                f"       terminal_count "
                f"  FROM {DEMO_USER}.ports ORDER BY port_code"
            )
            for code, name, country, ocean, lat, lon, terms in cur:
                if lat is None or lon is None:
                    continue
                ports.append({
                    "kind": "port",
                    "id": code,
                    "name": name,
                    "country": country,
                    "ocean_region": ocean,
                    "lat": float(lat),
                    "lng": float(lon),
                    "terminals": int(terms or 0),
                })

            # Vessels with current positions — restrict to vessels active on
            # voyages within identity's regions (if any).
            sql = (
                f"SELECT v.vessel_id, v.name, v.vessel_type, v.flag_country, "
                f"       v.capacity_teu, c.name AS carrier_name, "
                f"       p.latitude, p.longitude, p.speed_knots, p.heading_deg, "
                f"       voy.ocean_region "
                f"  FROM {DEMO_USER}.vessels v "
                f"  JOIN {DEMO_USER}.carriers c ON c.carrier_id = v.carrier_id "
                f"  JOIN {DEMO_USER}.vessel_positions p ON p.vessel_id = v.vessel_id "
                f"  LEFT JOIN ( "
                f"        SELECT vessel_id, MAX(ocean_region) KEEP (DENSE_RANK FIRST "
                f"               ORDER BY CASE WHEN status = 'IN_TRANSIT' THEN 0 ELSE 1 END, "
                f"                        departure_ts DESC) AS ocean_region "
                f"          FROM {DEMO_USER}.voyages GROUP BY vessel_id "
                f"  ) voy ON voy.vessel_id = v.vessel_id "
                f" WHERE 1=1 "
                f" {('AND voy.ocean_region IN (' + ','.join(f':rv{i}' for i in range(len(identity.regions))) + ')') if identity.regions else ''} "
            )
            binds = {f"rv{i}": r for i, r in enumerate(identity.regions or [])}
            cur.execute(sql, binds)
            for vid, name, vtype, flag, cap, carrier_name, lat, lon, kts, hdg, region in cur:
                if lat is None or lon is None:
                    continue
                vessels.append({
                    "kind": "vessel",
                    "id": int(vid),
                    "name": name,
                    "vessel_type": vtype,
                    "flag_country": flag,
                    "capacity_teu": int(cap or 0),
                    "carrier": carrier_name,
                    "ocean_region": region,
                    "lat": float(lat),
                    "lng": float(lon),
                    "speed_knots": float(kts) if kts is not None else 0.0,
                    "heading_deg": float(hdg) if hdg is not None else 0.0,
                })

            # Voyage arcs (origin → dest), with identity region filter.
            cur.execute(
                f"SELECT v.voyage_id, v.status, v.ocean_region, "
                f"       po.port_code, po.latitude, po.longitude, "
                f"       pd.port_code, pd.latitude, pd.longitude, "
                f"       ve.name AS vessel_name, ca.name AS carrier_name "
                f"  FROM {DEMO_USER}.voyages v "
                f"  JOIN {DEMO_USER}.ports po ON po.port_code = v.origin_code "
                f"  JOIN {DEMO_USER}.ports pd ON pd.port_code = v.dest_code "
                f"  JOIN {DEMO_USER}.vessels ve ON ve.vessel_id = v.vessel_id "
                f"  JOIN {DEMO_USER}.carriers ca ON ca.carrier_id = ve.carrier_id "
                f" WHERE 1=1 {region_clause} "
                f" ORDER BY v.voyage_id",
                region_binds,
            )
            for (vid, status, region, ocode, olat, olng,
                 dcode, dlat, dlng, vessel_name, carrier_name) in cur:
                if olat is None or dlat is None:
                    continue
                voyages.append({
                    "kind": "voyage",
                    "id": int(vid),
                    "status": status,
                    "ocean_region": region,
                    "vessel": vessel_name,
                    "carrier": carrier_name,
                    "origin": {"port_code": ocode, "lat": float(olat), "lng": float(olng)},
                    "destination": {"port_code": dcode, "lat": float(dlat), "lng": float(dlng)},
                })

            # Carrier summary — count of vessels per carrier on visible voyages.
            cur.execute(
                f"SELECT ca.name, ca.hq_country, COUNT(DISTINCT v.vessel_id) "
                f"  FROM {DEMO_USER}.carriers ca "
                f"  LEFT JOIN {DEMO_USER}.vessels ve ON ve.carrier_id = ca.carrier_id "
                f"  LEFT JOIN {DEMO_USER}.voyages v ON v.vessel_id = ve.vessel_id "
                f" WHERE 1=1 {region_clause} "
                f" GROUP BY ca.name, ca.hq_country "
                f" ORDER BY 3 DESC",
                region_binds,
            )
            for name, country, fleet in cur:
                centroid = COUNTRY_CENTROIDS.get(country)
                carrier_summary[name] = int(fleet or 0)
                if centroid is None:
                    continue
                carriers.append({
                    "kind": "carrier",
                    "id": name,
                    "name": name,
                    "country": country,
                    "active_vessels": int(fleet or 0),
                    "lat": centroid[0],
                    "lng": centroid[1],
                })

            # Containers — only when the identity is allowed to see them.
            # Position is the carrying vessel's current AIS-style point; we
            # nudge each container by a tiny per-id offset so a stack on the
            # same vessel becomes visually inspectable.
            if not containers_forbidden:
                cur.execute(
                    f"SELECT c.container_id, c.container_no, c.container_type, "
                    f"       c.consignor, c.consignee, c.status, "
                    f"       c.voyage_id, v.ocean_region, "
                    f"       ve.name AS vessel_name, ca.name AS carrier_name, "
                    f"       p.latitude, p.longitude, "
                    f"       po.port_code AS origin_code, pd.port_code AS dest_code, "
                    f"       (SELECT COUNT(*) FROM {DEMO_USER}.cargo_items ci "
                    f"          WHERE ci.container_id = c.container_id) AS cargo_count "
                    f"  FROM {DEMO_USER}.containers c "
                    f"  JOIN {DEMO_USER}.voyages v ON v.voyage_id = c.voyage_id "
                    f"  JOIN {DEMO_USER}.vessels ve ON ve.vessel_id = v.vessel_id "
                    f"  JOIN {DEMO_USER}.carriers ca ON ca.carrier_id = ve.carrier_id "
                    f"  LEFT JOIN {DEMO_USER}.vessel_positions p ON p.vessel_id = v.vessel_id "
                    f"  JOIN {DEMO_USER}.ports po ON po.port_code = v.origin_code "
                    f"  JOIN {DEMO_USER}.ports pd ON pd.port_code = v.dest_code "
                    f" WHERE p.latitude IS NOT NULL "
                    f" {region_clause} "
                    f" ORDER BY c.container_id ",
                    region_binds,
                )
                for (cid, cno, ctype, consignor, consignee, status, voyage_id,
                     region, vessel_name, carrier_name, lat, lng,
                     origin_code, dest_code, cargo_count) in cur:
                    if lat is None or lng is None:
                        continue
                    # Tiny lat/lng jitter (≤ ~5 km) so co-located containers
                    # on the same vessel don't perfectly overlap on the globe.
                    jitter = (int(cid) * 0.0173) % 0.08 - 0.04
                    containers.append({
                        "kind": "container",
                        "id": int(cid),
                        "container_no": cno,
                        "container_type": ctype,
                        "consignor": consignor,
                        "consignee": consignee,
                        "status": status,
                        "voyage_id": int(voyage_id),
                        "ocean_region": region,
                        "vessel": vessel_name,
                        "carrier": carrier_name,
                        "origin_code": origin_code,
                        "dest_code": dest_code,
                        "cargo_count": int(cargo_count or 0),
                        "lat": float(lat) + jitter,
                        "lng": float(lng) + jitter,
                    })

        return jsonify({
            "identity": identity.as_json(),
            "ports": ports,
            "vessels": vessels,
            "voyages": voyages,
            "carriers": carriers,
            "containers": containers,
            "containers_forbidden": containers_forbidden,
            "stats": {
                "ports": len(ports),
                "vessels": len(vessels),
                "voyages": len(voyages),
                "carriers": len(carriers),
                "containers": len(containers),
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

    Looks at port codes/names, vessel names, carrier names, and country names
    in priority order. Returns the first match with lat/lng so the front-end
    can fly the camera. Empty matches return 404 with a clear error.
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

        # 1. Port code (exact-ish) or name match.
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT port_code, name, country, ocean_region, latitude, longitude "
                f"  FROM {DEMO_USER}.ports "
                f" WHERE LOWER(port_code) = :exact OR LOWER(name) LIKE :needle "
                f"    OR LOWER(country) LIKE :needle "
                f" ORDER BY CASE WHEN LOWER(port_code) = :exact THEN 0 ELSE 1 END "
                f" FETCH FIRST 1 ROWS ONLY",
                exact=q.lower(), needle=needle,
            )
            row = cur.fetchone()
            if row:
                code, name, country, ocean, lat, lng = row
                return jsonify({
                    "kind": "port",
                    "id": code,
                    "name": name,
                    "country": country,
                    "ocean_region": ocean,
                    "lat": float(lat),
                    "lng": float(lng),
                })

        # 2. Vessel name — needs to also obey identity's region filter.
        region_clause, region_binds = _ident_region_filter(identity)
        with conn.cursor() as cur:
            sql = (
                f"SELECT ve.vessel_id, ve.name, p.latitude, p.longitude, "
                f"       ca.name, voy.ocean_region "
                f"  FROM {DEMO_USER}.vessels ve "
                f"  JOIN {DEMO_USER}.carriers ca ON ca.carrier_id = ve.carrier_id "
                f"  LEFT JOIN {DEMO_USER}.vessel_positions p ON p.vessel_id = ve.vessel_id "
                f"  LEFT JOIN ( "
                f"        SELECT vessel_id, MAX(ocean_region) KEEP (DENSE_RANK FIRST "
                f"               ORDER BY departure_ts DESC) AS ocean_region "
                f"          FROM {DEMO_USER}.voyages v WHERE 1=1 {region_clause} "
                f"         GROUP BY vessel_id "
                f"  ) voy ON voy.vessel_id = ve.vessel_id "
                f" WHERE LOWER(ve.name) LIKE :needle "
                f"   AND p.latitude IS NOT NULL "
                f" FETCH FIRST 1 ROWS ONLY"
            )
            cur.execute(sql, {"needle": needle, **region_binds})
            row = cur.fetchone()
            if row:
                vid, name, lat, lng, carrier, region = row
                return jsonify({
                    "kind": "vessel",
                    "id": int(vid),
                    "name": name,
                    "carrier": carrier,
                    "ocean_region": region,
                    "lat": float(lat),
                    "lng": float(lng),
                })

        # 3. Carrier name — anchor on HQ country centroid.
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT name, hq_country FROM {DEMO_USER}.carriers "
                f" WHERE LOWER(name) LIKE :needle "
                f" FETCH FIRST 1 ROWS ONLY",
                needle=needle,
            )
            row = cur.fetchone()
            if row:
                name, country = row
                centroid = COUNTRY_CENTROIDS.get(country)
                if centroid:
                    return jsonify({
                        "kind": "carrier",
                        "id": name,
                        "name": name,
                        "country": country,
                        "lat": centroid[0],
                        "lng": centroid[1],
                    })

        # 4. Container number (e.g. MAEU1234567) — anchored at the carrying
        #    vessel's current position. Only if containers aren't forbidden.
        if "SUPPLYCHAIN.CONTAINERS" not in identity.forbid_tables:
            with conn.cursor() as cur:
                sql = (
                    f"SELECT c.container_id, c.container_no, c.status, "
                    f"       v.ocean_region, ve.name, p.latitude, p.longitude "
                    f"  FROM {DEMO_USER}.containers c "
                    f"  JOIN {DEMO_USER}.voyages v ON v.voyage_id = c.voyage_id "
                    f"  JOIN {DEMO_USER}.vessels ve ON ve.vessel_id = v.vessel_id "
                    f"  LEFT JOIN {DEMO_USER}.vessel_positions p ON p.vessel_id = v.vessel_id "
                    f" WHERE LOWER(c.container_no) LIKE :needle "
                    f"   AND p.latitude IS NOT NULL "
                    f"   {region_clause} "
                    f" FETCH FIRST 1 ROWS ONLY"
                )
                cur.execute(sql, {"needle": needle, **region_binds})
                row = cur.fetchone()
                if row:
                    cid, cno, status, region, vessel_name, lat, lng = row
                    return jsonify({
                        "kind": "container",
                        "id": int(cid),
                        "name": cno,
                        "container_no": cno,
                        "status": status,
                        "ocean_region": region,
                        "vessel": vessel_name,
                        "lat": float(lat),
                        "lng": float(lng),
                    })

        # 5. Cargo description / HS code (if identity is allowed to see cargo).
        if "SUPPLYCHAIN.CARGO_ITEMS" not in identity.forbid_tables:
            with conn.cursor() as cur:
                sql = (
                    f"SELECT ci.cargo_item_id, ci.description, ci.hs_code, "
                    f"       pd.latitude, pd.longitude, pd.name, voy.ocean_region "
                    f"  FROM {DEMO_USER}.cargo_items ci "
                    f"  JOIN {DEMO_USER}.containers c ON c.container_id = ci.container_id "
                    f"  JOIN {DEMO_USER}.voyages voy ON voy.voyage_id = c.voyage_id "
                    f"  JOIN {DEMO_USER}.ports pd ON pd.port_code = voy.dest_code "
                    f" WHERE (LOWER(ci.description) LIKE :needle OR LOWER(ci.hs_code) LIKE :needle) "
                    f"   AND pd.latitude IS NOT NULL "
                    f"   {region_clause.replace('v.', 'voy.')} "
                    f" FETCH FIRST 1 ROWS ONLY"
                )
                cur.execute(sql, {"needle": needle, **region_binds})
                row = cur.fetchone()
                if row:
                    cid, desc, hs, lat, lng, port_name, region = row
                    return jsonify({
                        "kind": "cargo",
                        "id": int(cid),
                        "description": desc,
                        "hs_code": hs,
                        "ocean_region": region,
                        "destination_port": port_name,
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
