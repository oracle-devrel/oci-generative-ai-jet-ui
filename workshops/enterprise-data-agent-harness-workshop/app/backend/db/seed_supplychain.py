"""Supply-chain schema + spatial setup + seed data + JSON duality views.

Mirrors the notebook's Part 5.4 + Part 11.6 cells, condensed into a single
re-runnable function. Idempotent: re-running drops and re-creates objects with
the same content.
"""

from __future__ import annotations

import datetime as _dt
import random

import oracledb


SCHEMA = "SUPPLYCHAIN"


# ---------- DDL --------------------------------------------------------------
DDL = [
    """CREATE TABLE carriers (
         carrier_id      NUMBER(10) PRIMARY KEY,
         name            VARCHAR2(120) NOT NULL,
         hq_country      VARCHAR2(60),
         founded_year    NUMBER(4)
       )""",
    """CREATE TABLE ports (
         port_code       VARCHAR2(5) PRIMARY KEY,
         name            VARCHAR2(120) NOT NULL,
         country         VARCHAR2(60),
         ocean_region    VARCHAR2(20) NOT NULL,
         terminal_count  NUMBER(3),
         latitude        NUMBER(10,6),
         longitude       NUMBER(10,6),
         location        SDO_GEOMETRY
       )""",
    """CREATE TABLE vessels (
         vessel_id       NUMBER(10) PRIMARY KEY,
         carrier_id      NUMBER(10) NOT NULL REFERENCES carriers(carrier_id),
         name            VARCHAR2(120) NOT NULL,
         imo_number      VARCHAR2(10) UNIQUE,
         vessel_type     VARCHAR2(20) NOT NULL,
         capacity_teu    NUMBER(7),
         year_built      NUMBER(4),
         flag_country    VARCHAR2(60)
       )""",
    """CREATE TABLE voyages (
         voyage_id       NUMBER(10) PRIMARY KEY,
         vessel_id       NUMBER(10) NOT NULL REFERENCES vessels(vessel_id),
         origin_code     VARCHAR2(5) NOT NULL REFERENCES ports(port_code),
         dest_code       VARCHAR2(5) NOT NULL REFERENCES ports(port_code),
         departure_ts    TIMESTAMP,
         eta_ts          TIMESTAMP,
         status          VARCHAR2(20) NOT NULL,
         ocean_region    VARCHAR2(20) NOT NULL
       )""",
    """CREATE TABLE vessel_positions (
         vessel_id       NUMBER(10) PRIMARY KEY REFERENCES vessels(vessel_id),
         position_ts     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
         latitude        NUMBER(10,6),
         longitude       NUMBER(11,6),
         speed_knots     NUMBER(5,2),
         heading_deg     NUMBER(5,2),
         position        SDO_GEOMETRY
       )""",
    """CREATE TABLE containers (
         container_id    NUMBER(10) PRIMARY KEY,
         voyage_id       NUMBER(10) NOT NULL REFERENCES voyages(voyage_id),
         container_no    VARCHAR2(11) UNIQUE NOT NULL,
         container_type  VARCHAR2(20) NOT NULL,
         consignor       VARCHAR2(120),
         consignee       VARCHAR2(120),
         status          VARCHAR2(20) NOT NULL
       )""",
    """CREATE TABLE cargo_items (
         cargo_item_id   NUMBER(10) PRIMARY KEY,
         container_id    NUMBER(10) NOT NULL REFERENCES containers(container_id),
         hs_code         VARCHAR2(10),
         description     VARCHAR2(400),
         quantity        NUMBER(10),
         unit_value_cents NUMBER(15),
         weight_kg       NUMBER(10,2)
       )""",
    "COMMENT ON COLUMN vessels.capacity_teu IS 'Cargo capacity in TEU (20-foot equivalent units); never tons.'",
    "COMMENT ON COLUMN cargo_items.unit_value_cents IS 'Per-unit declared value in USD CENTS, never dollars.'",
    "COMMENT ON TABLE ports IS 'Container ports worldwide; location is SDO_GEOMETRY (WGS84, SRID 8307).'",
    "COMMENT ON TABLE voyages IS 'Vessel journeys; ocean_region drives the §14.4 DDS row policies.'",
    "COMMENT ON TABLE vessel_positions IS 'Current AIS-style positions; position is SDO_GEOMETRY (WGS84).'",
]

SPATIAL = [
    "DELETE FROM USER_SDO_GEOM_METADATA WHERE table_name IN ('PORTS', 'VESSEL_POSITIONS')",
    """INSERT INTO USER_SDO_GEOM_METADATA (table_name, column_name, diminfo, srid)
       VALUES ('PORTS', 'LOCATION',
               SDO_DIM_ARRAY(
                 SDO_DIM_ELEMENT('LON', -180, 180, 0.005),
                 SDO_DIM_ELEMENT('LAT',  -90,  90, 0.005)
               ), 8307)""",
    """INSERT INTO USER_SDO_GEOM_METADATA (table_name, column_name, diminfo, srid)
       VALUES ('VESSEL_POSITIONS', 'POSITION',
               SDO_DIM_ARRAY(
                 SDO_DIM_ELEMENT('LON', -180, 180, 0.005),
                 SDO_DIM_ELEMENT('LAT',  -90,  90, 0.005)
               ), 8307)""",
    "CREATE INDEX ports_loc_sx ON ports(location) INDEXTYPE IS MDSYS.SPATIAL_INDEX_V2",
    "CREATE INDEX vpos_loc_sx  ON vessel_positions(position) INDEXTYPE IS MDSYS.SPATIAL_INDEX_V2",
]

# ---------- Reference data --------------------------------------------------
CARRIERS = [
    (1, "Maersk", "Denmark", 1904), (2, "MSC", "Switzerland", 1970),
    (3, "CMA CGM", "France", 1978), (4, "COSCO", "China", 1961),
    (5, "Hapag-Lloyd", "Germany", 1970), (6, "ONE", "Japan", 2017),
    (7, "Evergreen", "Taiwan", 1968), (8, "Yang Ming", "Taiwan", 1972),
    (9, "HMM", "South Korea", 1976), (10, "ZIM", "Israel", 1945),
    (11, "OOCL", "Hong Kong", 1969), (12, "Wan Hai", "Taiwan", 1965),
    (13, "PIL", "Singapore", 1967), (14, "Matson", "USA", 1882),
    (15, "ANL", "Australia", 1956),
]

PORTS = [
    ("SGSIN", "Singapore",         "Singapore",   "INDIAN",         62,    1.264900,  103.832600),
    ("CNSHA", "Shanghai",          "China",       "PACIFIC",        43,   31.235400,  121.473700),
    ("CNSHK", "Shenzhen Yantian",  "China",       "PACIFIC",        20,   22.564200,  114.272100),
    ("CNNGB", "Ningbo-Zhoushan",   "China",       "PACIFIC",        38,   29.868400,  121.836700),
    ("HKHKG", "Hong Kong",         "Hong Kong",   "PACIFIC",        24,   22.319300,  114.169400),
    ("KRPUS", "Busan",             "South Korea", "PACIFIC",        21,   35.102800,  129.040300),
    ("AEJEA", "Jebel Ali (Dubai)", "UAE",         "INDIAN",         15,   25.012300,   55.061700),
    ("MYTPP", "Tanjung Pelepas",   "Malaysia",    "INDIAN",         11,    1.366000,  103.560000),
    ("LKCMB", "Colombo",           "Sri Lanka",   "INDIAN",          5,    6.951900,   79.851800),
    ("OMSLL", "Salalah",           "Oman",        "INDIAN",          4,   17.018300,   54.092400),
    ("USLAX", "Los Angeles",       "USA",         "PACIFIC",        25,   33.732500, -118.262000),
    ("USLGB", "Long Beach",        "USA",         "PACIFIC",        22,   33.760100, -118.214800),
    ("USNYC", "New York/Newark",   "USA",         "ATLANTIC",       16,   40.683800,  -74.137300),
    ("USSAV", "Savannah",          "USA",         "ATLANTIC",        9,   32.083200,  -81.097100),
    ("USHOU", "Houston",           "USA",         "ATLANTIC",       10,   29.730400,  -95.246700),
    ("NLRTM", "Rotterdam",         "Netherlands", "ATLANTIC",       30,   51.924400,    4.477700),
    ("DEHAM", "Hamburg",           "Germany",     "ATLANTIC",       17,   53.551100,    9.993700),
    ("BEANR", "Antwerp",           "Belgium",     "ATLANTIC",       21,   51.221300,    4.401800),
    ("FRLEH", "Le Havre",          "France",      "ATLANTIC",       12,   49.490000,    0.107400),
    ("GBFXT", "Felixstowe",        "UK",          "ATLANTIC",        8,   51.961100,    1.351200),
    ("ESVLC", "Valencia",          "Spain",       "MEDITERRANEAN",  10,   39.469900,   -0.376300),
    ("ESALG", "Algeciras",         "Spain",       "MEDITERRANEAN",   7,   36.131500,   -5.453300),
    ("ITGOA", "Genoa",             "Italy",       "MEDITERRANEAN",   8,   44.405600,    8.946300),
    ("EGSCB", "Suez Canal South",  "Egypt",       "MEDITERRANEAN",   1,   29.967600,   32.549400),
    ("JPYOK", "Yokohama / Tokyo",  "Japan",       "PACIFIC",        18,   35.443900,  139.638100),
]

VESSEL_NAMES = {
    1:  ["Maersk Madrid", "Maersk Edinburgh", "Maersk Hong Kong", "Maersk Tukang"],
    2:  ["MSC Oscar", "MSC Gulsun", "MSC Eloane", "MSC Mia"],
    3:  ["CMA CGM Marco Polo", "CMA CGM Alexander", "CMA CGM Jacques Saade"],
    4:  ["COSCO Shipping Universe", "COSCO Pisces", "COSCO Cancer"],
    5:  ["Hapag-Lloyd Berlin Express", "Hapag-Lloyd Hamburg Express"],
    6:  ["ONE Apus", "ONE Stork"],
    7:  ["Ever Ace", "Ever Given", "Ever Globe"],
    8:  ["YM Witness", "YM Wreath"],
    9:  ["HMM Algeciras", "HMM Oslo"],
    10: ["ZIM Mount Everest", "ZIM Kingston"],
    11: ["OOCL Hong Kong", "OOCL Spain"],
    12: ["Wan Hai 805"], 13: ["Kota Pekarang"], 14: ["Matson Daniel K. Inouye"],
    15: ["ANL Wahroonga"],
}

CARGO_CATALOG = [
    ("8517", "Smartphones, retail-packed", 28000, 0.18, "DRY"),
    ("8528", "LED televisions, 50-inch class", 32000, 18.5, "DRY"),
    ("8703", "Passenger automobiles", 2800000, 1500, "RORO"),
    ("8714", "Bicycle parts and accessories", 1200, 1.4, "DRY"),
    ("8419", "Industrial heat exchangers", 580000, 480, "OPEN_TOP"),
    ("3004", "Pharmaceuticals, packaged", 45000, 0.5, "DRY"),
    ("3004", "Pharmaceuticals, refrigerated", 89000, 0.5, "REEFER"),
    ("0303", "Frozen seafood, salmon", 4500, 1.0, "REEFER"),
    ("0810", "Fresh berries", 2800, 1.0, "REEFER"),
    ("0901", "Roasted coffee beans, bulk", 1800, 1.0, "DRY"),
    ("8506", "Lithium-ion battery cells (HAZ class 9)", 8500, 0.4, "HAZMAT"),
    ("3105", "Fertilizer, ammonium nitrate", 850, 25, "HAZMAT"),
    ("2710", "Petroleum lubricants, drums", 1900, 200, "HAZMAT"),
    ("9018", "Medical instruments and apparatus", 240000, 4.2, "DRY"),
    ("8471", "Personal computers and laptops", 95000, 2.3, "DRY"),
    ("9403", "Office furniture, knock-down", 12000, 35, "DRY"),
    ("4202", "Designer luggage and handbags", 35000, 1.8, "DRY"),
    ("6203", "Men's apparel, woven", 4500, 0.4, "DRY"),
    ("6204", "Women's apparel, woven", 5200, 0.4, "DRY"),
    ("8482", "Industrial ball bearings, assorted", 1900, 0.6, "DRY"),
    ("7308", "Steel structures, prefab", 32000, 200, "OPEN_TOP"),
    ("4011", "Pneumatic tires, passenger car", 9500, 8.5, "DRY"),
    ("8407", "Marine engines, spare parts", 165000, 75, "DRY"),
    ("8501", "Industrial electric motors", 92000, 110, "DRY"),
    ("3923", "Plastic articles for packing", 350, 0.05, "DRY"),
    ("4818", "Toilet paper and tissues, bulk", 280, 0.4, "DRY"),
    ("8504", "Power transformers", 145000, 320, "OPEN_TOP"),
    ("9405", "LED lighting fixtures", 5500, 1.2, "DRY"),
    ("0808", "Apples, fresh", 180, 0.18, "REEFER"),
    ("8703", "Electric vehicles, complete", 4200000, 2200, "RORO"),
]

CONSIGNORS = [
    "Foxconn Technology Group", "Bosch Automotive", "Samsung SDI", "Tesla Inc.",
    "Volkswagen AG", "Toyota Motor Corp.", "Lenovo Group", "Apple Inc.",
    "Nestle SA", "IKEA", "Maersk Logistics", "Caterpillar Inc.", "BASF SE",
    "Pfizer Inc.", "Glencore Agriculture",
]
CONSIGNEES = [
    "Walmart Inc.", "Costco Wholesale", "Amazon.com Services", "Best Buy",
    "Home Depot", "Target Corp.", "Carrefour", "Tesco Stores", "Aldi Nord",
    "El Corte Ingles", "Loblaws", "Coles Group",
    "Sumitomo Electric Industries", "Pemex", "Petrobras",
]

VOYAGE_REGION_PAIRS = {
    ("PACIFIC", "ATLANTIC"): "PACIFIC", ("ATLANTIC", "PACIFIC"): "ATLANTIC",
    ("INDIAN", "MEDITERRANEAN"): "INDIAN", ("MEDITERRANEAN", "INDIAN"): "MEDITERRANEAN",
    ("PACIFIC", "INDIAN"): "PACIFIC", ("INDIAN", "PACIFIC"): "INDIAN",
    ("ATLANTIC", "MEDITERRANEAN"): "ATLANTIC", ("MEDITERRANEAN", "ATLANTIC"): "MEDITERRANEAN",
    ("ATLANTIC", "INDIAN"): "INDIAN", ("INDIAN", "ATLANTIC"): "INDIAN",
    ("PACIFIC", "MEDITERRANEAN"): "PACIFIC", ("MEDITERRANEAN", "PACIFIC"): "MEDITERRANEAN",
}


def _drop_existing(conn):
    for v in ["voyage_dv", "vessel_dv"]:
        try:
            with conn.cursor() as cur:
                cur.execute(f"DROP VIEW {v}")
        except oracledb.DatabaseError:
            pass
    for t in ["cargo_items", "containers", "vessel_positions", "voyages",
              "vessels", "ports", "carriers"]:
        try:
            with conn.cursor() as cur:
                cur.execute(f"DROP TABLE {t} CASCADE CONSTRAINTS PURGE")
        except oracledb.DatabaseError:
            pass


def _create_schema(conn):
    with conn.cursor() as cur:
        for stmt in DDL:
            cur.execute(stmt)
    conn.commit()


def _create_spatial(conn):
    with conn.cursor() as cur:
        for stmt in SPATIAL:
            try:
                cur.execute(stmt)
            except oracledb.DatabaseError as e:
                if e.args[0].code in (955, 1408, 13223, 13226, 29855):
                    continue
                raise
    conn.commit()


def _voyage_region(origin_port_code: str, dest_port_code: str) -> str:
    op = next(p[3] for p in PORTS if p[0] == origin_port_code)
    dp = next(p[3] for p in PORTS if p[0] == dest_port_code)
    if op == dp:
        return op
    return VOYAGE_REGION_PAIRS.get((op, dp), op)


def _build_seed():
    """Generate deterministic seed data (random.seed(42))."""
    random.seed(42)

    vessels = []
    vid = 1
    for cid, names in VESSEL_NAMES.items():
        for name in names:
            vtype = "CONTAINER"
            cap = random.choice([5500, 8800, 11000, 14000, 18000, 20000, 23000, 24000])
            year = random.choice([2014, 2015, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024])
            flag = random.choice(["Denmark", "Liberia", "Panama", "Singapore",
                                  "Marshall Islands", "Hong Kong", "Malta", "Bahamas"])
            imo = f"IMO{random.randint(9000000, 9999999)}"
            vessels.append((vid, cid, name, imo, vtype, cap, year, flag))
            vid += 1

    statuses = ["ACTIVE"] * 30 + ["DELAYED"] * 10 + ["SCHEDULED"] * 10 + ["COMPLETED"] * 10
    random.shuffle(statuses)
    voyages = []
    now = _dt.datetime.utcnow()
    for i in range(60):
        o = random.choice(PORTS)[0]
        d = random.choice([p for p in PORTS if p[0] != o])[0]
        st = statuses[i]
        if st == "SCHEDULED":
            dep = now + _dt.timedelta(days=random.randint(2, 30))
            eta = dep + _dt.timedelta(days=random.randint(7, 35))
        elif st == "COMPLETED":
            dep = now - _dt.timedelta(days=random.randint(40, 90))
            eta = dep + _dt.timedelta(days=random.randint(7, 35))
        elif st == "DELAYED":
            dep = now - _dt.timedelta(days=random.randint(10, 30))
            eta = now + _dt.timedelta(days=random.randint(3, 14))
        else:
            dep = now - _dt.timedelta(days=random.randint(2, 20))
            eta = now + _dt.timedelta(days=random.randint(5, 25))
        voyages.append((i + 1, (i % len(vessels)) + 1, o, d, dep, eta, st,
                        _voyage_region(o, d)))

    ports_by = {p[0]: p for p in PORTS}
    positions = []
    seen = set()
    for vy in voyages:
        _, vessel_id, o_code, d_code, _, _, st, _ = vy
        if st not in ("ACTIVE", "DELAYED") or vessel_id in seen:
            continue
        seen.add(vessel_id)
        op, dp = ports_by[o_code], ports_by[d_code]
        t = random.uniform(0.30, 0.70)
        lat = op[5] + (dp[5] - op[5]) * t + random.uniform(-1.5, 1.5)
        lon = op[6] + (dp[6] - op[6]) * t + random.uniform(-1.5, 1.5)
        positions.append((vessel_id, lat, lon,
                          round(random.uniform(12.0, 22.5), 2),
                          round(random.uniform(0, 360), 2)))

    container_types = ["DRY", "DRY", "DRY", "REEFER", "HAZMAT", "OPEN_TOP", "DRY"]
    container_statuses = ["LOADED", "IN_TRANSIT", "DISCHARGED", "CUSTOMS_HOLD"]
    containers, cargo_items = [], []
    cid = 1
    cargo_id = 1
    for vy in voyages:
        voyage_id, _, _, _, _, _, st, _ = vy
        n = (random.randint(0, 2) if st == "COMPLETED"
             else random.randint(1, 3) if st == "SCHEDULED"
             else random.randint(2, 5))
        for _ in range(n):
            ct = random.choice(container_types)
            cs = random.choice(container_statuses)
            containers.append((cid, voyage_id,
                               f"MSCU{random.randint(1000000, 9999999)}",
                               ct, random.choice(CONSIGNORS),
                               random.choice(CONSIGNEES), cs))
            pool = [c for c in CARGO_CATALOG if c[4] == ct] or CARGO_CATALOG
            for _ in range(random.randint(1, 3)):
                hs, desc, val, wt, _ = random.choice(pool)
                qty = random.choice([10, 25, 50, 100, 200, 500, 1000])
                cargo_items.append((cargo_id, cid, hs, desc, qty,
                                    int(val * random.uniform(0.85, 1.15)),
                                    round(wt * qty, 2)))
                cargo_id += 1
            cid += 1

    return vessels, voyages, positions, containers, cargo_items


def _insert_data(conn, vessels, voyages, positions, containers, cargo_items):
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO carriers VALUES (:1, :2, :3, :4)", CARRIERS,
        )
        # Named binds — SDO_POINT_TYPE re-references lat/lon, which would otherwise
        # trip DPY-4009 (thin driver counts every positional `:N` occurrence).
        cur.executemany(
            "INSERT INTO ports (port_code, name, country, ocean_region, terminal_count, "
            "                   latitude, longitude, location) "
            "VALUES (:code, :name, :country, :region, :terminals, :lat, :lon, "
            "        SDO_GEOMETRY(2001, 8307, SDO_POINT_TYPE(:lon, :lat, NULL), NULL, NULL))",
            [
                {"code": p[0], "name": p[1], "country": p[2], "region": p[3],
                 "terminals": p[4], "lat": p[5], "lon": p[6]}
                for p in PORTS
            ],
        )
        cur.executemany(
            "INSERT INTO vessels VALUES (:1, :2, :3, :4, :5, :6, :7, :8)", vessels,
        )
        cur.executemany(
            "INSERT INTO voyages VALUES (:1, :2, :3, :4, :5, :6, :7, :8)", voyages,
        )
        cur.executemany(
            "INSERT INTO vessel_positions (vessel_id, latitude, longitude, "
            "                              speed_knots, heading_deg, position) "
            "VALUES (:vid, :lat, :lon, :speed, :heading, "
            "        SDO_GEOMETRY(2001, 8307, SDO_POINT_TYPE(:lon, :lat, NULL), NULL, NULL))",
            [
                {"vid": p[0], "lat": p[1], "lon": p[2], "speed": p[3], "heading": p[4]}
                for p in positions
            ],
        )
        cur.executemany(
            "INSERT INTO containers VALUES (:1, :2, :3, :4, :5, :6, :7)", containers,
        )
        cur.executemany(
            "INSERT INTO cargo_items VALUES (:1, :2, :3, :4, :5, :6, :7)", cargo_items,
        )
    conn.commit()


# ---------- Duality views ----------------------------------------------------
DV_DDL = [
    """CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW voyage_dv AS
       SELECT JSON {
         '_id'         : v.voyage_id,
         'status'      : v.status,
         'oceanRegion' : v.ocean_region,
         'departureTs' : v.departure_ts,
         'etaTs'       : v.eta_ts,
         'origin'      : (SELECT JSON {
                            'portCode' : po.port_code, 'name' : po.name,
                            'country' : po.country,
                            'latitude' : po.latitude, 'longitude' : po.longitude
                          } FROM ports po WHERE po.port_code = v.origin_code),
         'destination' : (SELECT JSON {
                            'portCode' : pd.port_code, 'name' : pd.name,
                            'country' : pd.country,
                            'latitude' : pd.latitude, 'longitude' : pd.longitude
                          } FROM ports pd WHERE pd.port_code = v.dest_code),
         'vessel'      : (SELECT JSON {
                            'vesselId' : ve.vessel_id, 'name' : ve.name,
                            'imoNumber' : ve.imo_number,
                            'vesselType' : ve.vessel_type,
                            'capacityTeu' : ve.capacity_teu,
                            'flagCountry' : ve.flag_country,
                            'carrier' : (SELECT JSON {
                                           'carrierId' : ca.carrier_id,
                                           'name' : ca.name,
                                           'hqCountry' : ca.hq_country
                                         } FROM carriers ca WHERE ca.carrier_id = ve.carrier_id)
                          } FROM vessels ve WHERE ve.vessel_id = v.vessel_id),
         'containers'  : [SELECT JSON {
                            'containerId' : c.container_id,
                            'containerNo' : c.container_no,
                            'containerType' : c.container_type,
                            'consignor' : c.consignor,
                            'consignee' : c.consignee,
                            'status' : c.status,
                            'cargo' : [SELECT JSON {
                                         'cargoItemId' : ci.cargo_item_id,
                                         'hsCode' : ci.hs_code,
                                         'description' : ci.description,
                                         'quantity' : ci.quantity,
                                         'unitValueCents' : ci.unit_value_cents,
                                         'weightKg' : ci.weight_kg
                                       } FROM cargo_items ci WHERE ci.container_id = c.container_id]
                          } FROM containers c WHERE c.voyage_id = v.voyage_id]
       } FROM voyages v""",

    """CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW vessel_dv AS
       SELECT JSON {
         '_id'         : v.vessel_id,
         'name'        : v.name,
         'imoNumber'   : v.imo_number,
         'vesselType'  : v.vessel_type,
         'capacityTeu' : v.capacity_teu,
         'yearBuilt'   : v.year_built,
         'flagCountry' : v.flag_country,
         'carrier'     : (SELECT JSON {
                            'carrierId' : c.carrier_id, 'name' : c.name,
                            'hqCountry' : c.hq_country
                          } FROM carriers c WHERE c.carrier_id = v.carrier_id),
         'position'    : (SELECT JSON {
                            'positionTs' : p.position_ts,
                            'latitude'   : p.latitude,
                            'longitude'  : p.longitude,
                            'speedKnots' : p.speed_knots,
                            'headingDeg' : p.heading_deg
                          } FROM vessel_positions p WHERE p.vessel_id = v.vessel_id)
       } FROM vessels v""",
]


def _create_duality_views(conn):
    for stmt in DV_DDL:
        try:
            with conn.cursor() as cur:
                cur.execute(stmt)
            head = stmt.strip().split("\n", 1)[0]
            print(f"  OK: {head[:80]}")
        except oracledb.DatabaseError as e:
            code_ = e.args[0].code
            if code_ in (900, 901, 922, 2000):
                print(f"  !! duality view DDL not supported on this image (ORA-{code_:05d}); skipping")
                return
            raise
    conn.commit()


def seed(conn):
    """Run the full pipeline: drop → create → spatial → seed → duality views."""
    print("Dropping existing supply chain objects...")
    _drop_existing(conn)

    print("Creating tables...")
    _create_schema(conn)

    print("Wiring spatial metadata + indexes...")
    _create_spatial(conn)

    print("Generating deterministic seed data...")
    vessels, voyages, positions, containers, cargo_items = _build_seed()

    print(f"Inserting: {len(CARRIERS)} carriers, {len(PORTS)} ports, "
          f"{len(vessels)} vessels, {len(voyages)} voyages, "
          f"{len(positions)} positions, {len(containers)} containers, "
          f"{len(cargo_items)} cargo items...")
    _insert_data(conn, vessels, voyages, positions, containers, cargo_items)

    print("Creating JSON Relational Duality Views (voyage_dv, vessel_dv)...")
    _create_duality_views(conn)

    print("\nSUPPLYCHAIN seeded.")
