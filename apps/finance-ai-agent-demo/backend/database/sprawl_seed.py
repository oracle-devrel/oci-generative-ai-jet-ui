"""Seed data for the sprawl architecture: PostgreSQL, Neo4j, MongoDB, Qdrant."""

import json
import uuid

from qdrant_client.models import PointStruct

# ---------------------------------------------------------------------------
# Seed data definitions (shared across functions)
# ---------------------------------------------------------------------------

RELATIONSHIP_MANAGERS = [
    ("RM-001", "Sarah Chen", "North America", "Wealth Management", "sarah.chen@firm.com"),
    ("RM-002", "James Morrison", "North America", "Institutional", "james.morrison@firm.com"),
    ("RM-003", "Priya Sharma", "APAC", "Wealth Management", "priya.sharma@firm.com"),
    ("RM-004", "Michael O'Brien", "EMEA", "Private Banking", "michael.obrien@firm.com"),
    ("RM-005", "Elena Rodriguez", "LATAM", "Corporate", "elena.rodriguez@firm.com"),
]

CLIENT_ACCOUNTS = [
    {
        "account_id": "ACC-001",
        "client_name": "Smith Family Trust",
        "account_type": "trust",
        "risk_profile": "moderate",
        "aum": 4250000.00,
        "rm": "Sarah Chen",
        "date": "2019-03-15",
        "metadata": {
            "investment_preferences": {
                "esg_mandate": True,
                "max_single_position": 0.10,
                "preferred_sectors": ["technology", "healthcare"],
                "excluded_sectors": ["tobacco", "firearms"],
            },
            "restricted_securities": ["PMI", "RGR", "SWBI"],
            "tax_status": "tax-exempt",
            "distribution_schedule": "quarterly",
        },
        "lon": -73.9857,
        "lat": 40.7484,
    },
    {
        "account_id": "ACC-002",
        "client_name": "Apex Capital Partners",
        "account_type": "corporate",
        "risk_profile": "aggressive",
        "aum": 28500000.00,
        "rm": "James Morrison",
        "date": "2018-06-01",
        "metadata": {
            "investment_preferences": {
                "esg_mandate": False,
                "max_single_position": 0.15,
                "preferred_sectors": ["technology", "energy", "financials"],
                "excluded_sectors": [],
            },
            "restricted_securities": [],
            "entity_type": "hedge_fund",
            "leverage_allowed": True,
        },
        "lon": -71.0589,
        "lat": 42.3601,
    },
    {
        "account_id": "ACC-003",
        "client_name": "Margaret Williams",
        "account_type": "individual",
        "risk_profile": "conservative",
        "aum": 1850000.00,
        "rm": "Michael O'Brien",
        "date": "2021-01-10",
        "metadata": {
            "investment_preferences": {
                "esg_mandate": False,
                "max_single_position": 0.08,
                "preferred_sectors": ["fixed_income", "utilities", "consumer_staples"],
                "excluded_sectors": [],
            },
            "restricted_securities": [],
            "income_focus": True,
            "distribution_schedule": "monthly",
        },
        "lon": -122.4194,
        "lat": 37.7749,
    },
    {
        "account_id": "ACC-004",
        "client_name": "TechVentures LLC",
        "account_type": "corporate",
        "risk_profile": "aggressive",
        "aum": 15200000.00,
        "rm": "Priya Sharma",
        "date": "2020-09-20",
        "metadata": {
            "investment_preferences": {
                "esg_mandate": True,
                "max_single_position": 0.15,
                "preferred_sectors": ["technology", "semiconductors"],
                "excluded_sectors": ["fossil_fuels", "tobacco"],
            },
            "restricted_securities": ["XOM", "CVX"],
        },
        "lon": -118.2437,
        "lat": 34.0522,
    },
    {
        "account_id": "ACC-005",
        "client_name": "Johnson Pension Fund",
        "account_type": "trust",
        "risk_profile": "conservative",
        "aum": 62000000.00,
        "rm": "James Morrison",
        "date": "2015-09-01",
        "metadata": {
            "investment_preferences": {
                "esg_mandate": True,
                "max_single_position": 0.05,
                "preferred_sectors": ["fixed_income", "real_estate", "utilities"],
                "excluded_sectors": ["gambling", "tobacco"],
            },
            "restricted_securities": ["LVS", "WYNN", "MGM"],
            "liability_matching": True,
            "duration_target_years": 12,
        },
        "lon": -87.6298,
        "lat": 41.8781,
    },
]

RM_LOCATIONS = [
    ("RM-001", -73.9857, 40.7484),  # New York
    ("RM-002", -87.6298, 41.8781),  # Chicago
    ("RM-003", 103.8198, 1.3521),  # Singapore
    ("RM-004", -0.1276, 51.5074),  # London
    ("RM-005", -46.6333, -23.5505),  # São Paulo
]

PORTFOLIO_HOLDINGS = [
    # Smith Family Trust (ACC-001)
    (
        "H-001",
        "ACC-001",
        "equity",
        "Apple Inc.",
        "AAPL",
        850,
        148750.00,
        142.50,
        "2022-03-15",
        "Technology",
        "US",
        5.5,
    ),
    (
        "H-002",
        "ACC-001",
        "equity",
        "Microsoft Corp.",
        "MSFT",
        600,
        246000.00,
        380.00,
        "2021-11-01",
        "Technology",
        "US",
        4.8,
    ),
    (
        "H-003",
        "ACC-001",
        "equity",
        "Johnson & Johnson",
        "JNJ",
        1200,
        186000.00,
        165.00,
        "2020-06-10",
        "Healthcare",
        "US",
        3.2,
    ),
    (
        "H-004",
        "ACC-001",
        "fixed_income",
        "US Treasury 10Y",
        "UST10Y",
        500000,
        485000.00,
        98.50,
        "2023-01-05",
        "Government",
        "US",
        1.5,
    ),
    (
        "H-005",
        "ACC-001",
        "equity",
        "Alphabet Inc.",
        "GOOGL",
        400,
        56800.00,
        135.00,
        "2022-08-20",
        "Technology",
        "US",
        5.0,
    ),
    # Apex Capital Partners (ACC-002)
    (
        "H-010",
        "ACC-002",
        "equity",
        "Tesla Inc.",
        "TSLA",
        3000,
        750000.00,
        220.00,
        "2022-01-10",
        "Technology",
        "US",
        9.0,
    ),
    (
        "H-011",
        "ACC-002",
        "equity",
        "Amazon.com",
        "AMZN",
        2500,
        437500.00,
        170.00,
        "2021-06-15",
        "Technology",
        "US",
        6.5,
    ),
    (
        "H-012",
        "ACC-002",
        "equity",
        "ExxonMobil",
        "XOM",
        5000,
        525000.00,
        105.00,
        "2022-04-01",
        "Energy",
        "US",
        5.5,
    ),
    (
        "H-013",
        "ACC-002",
        "alternatives",
        "Bitcoin Trust",
        "GBTC",
        10000,
        450000.00,
        38.00,
        "2023-02-14",
        "Crypto",
        "Global",
        9.5,
    ),
    (
        "H-014",
        "ACC-002",
        "equity",
        "JPMorgan Chase",
        "JPM",
        3500,
        630000.00,
        160.00,
        "2020-09-20",
        "Financials",
        "US",
        5.0,
    ),
    # Margaret Williams (ACC-003)
    (
        "H-020",
        "ACC-003",
        "fixed_income",
        "US Treasury 5Y",
        "UST5Y",
        400000,
        392000.00,
        99.00,
        "2023-03-01",
        "Government",
        "US",
        1.0,
    ),
    (
        "H-021",
        "ACC-003",
        "equity",
        "Procter & Gamble",
        "PG",
        800,
        128000.00,
        155.00,
        "2021-07-10",
        "Consumer Staples",
        "US",
        2.5,
    ),
    (
        "H-022",
        "ACC-003",
        "equity",
        "Duke Energy",
        "DUK",
        1500,
        142500.00,
        95.00,
        "2022-05-20",
        "Utilities",
        "US",
        2.0,
    ),
    (
        "H-023",
        "ACC-003",
        "fixed_income",
        "Corporate Bond ETF",
        "LQD",
        2000,
        220000.00,
        110.00,
        "2022-11-15",
        "Fixed Income",
        "US",
        2.5,
    ),
    # TechVentures (ACC-004)
    (
        "H-030",
        "ACC-004",
        "equity",
        "NVIDIA Corp.",
        "NVDA",
        5000,
        3750000.00,
        480.00,
        "2023-03-10",
        "Technology",
        "US",
        8.5,
    ),
    (
        "H-031",
        "ACC-004",
        "equity",
        "AMD",
        "AMD",
        8000,
        1200000.00,
        145.00,
        "2022-07-01",
        "Semiconductors",
        "US",
        7.5,
    ),
    (
        "H-032",
        "ACC-004",
        "equity",
        "Taiwan Semiconductor",
        "TSM",
        6000,
        660000.00,
        105.00,
        "2022-09-15",
        "Semiconductors",
        "APAC",
        6.0,
    ),
    (
        "H-033",
        "ACC-004",
        "equity",
        "Microsoft Corp.",
        "MSFT",
        2000,
        820000.00,
        380.00,
        "2021-12-01",
        "Technology",
        "US",
        4.8,
    ),
    # Johnson Pension Fund (ACC-005)
    (
        "H-040",
        "ACC-005",
        "fixed_income",
        "US Treasury 30Y",
        "UST30Y",
        5000000,
        4850000.00,
        97.00,
        "2020-01-15",
        "Government",
        "US",
        1.5,
    ),
    (
        "H-041",
        "ACC-005",
        "fixed_income",
        "Investment Grade Bonds",
        "VCIT",
        3000000,
        2880000.00,
        96.00,
        "2021-04-01",
        "Fixed Income",
        "US",
        2.0,
    ),
    (
        "H-042",
        "ACC-005",
        "alternatives",
        "Real Estate Fund",
        "VNQ",
        50000,
        4500000.00,
        90.00,
        "2019-06-20",
        "Real Estate",
        "US",
        4.0,
    ),
    (
        "H-043",
        "ACC-005",
        "equity",
        "NextEra Energy",
        "NEE",
        15000,
        1050000.00,
        70.00,
        "2022-02-10",
        "Utilities",
        "US",
        3.0,
    ),
]

COMPLIANCE_RULES = [
    (
        "CR-001",
        "Single Position Concentration Limit",
        "concentration",
        "No single equity position shall exceed 10% of total portfolio value for moderate-risk accounts, or 15% for aggressive accounts.",
        "percentage",
        0.10,
        "SEC",
        "2020-01-01",
    ),
    (
        "CR-002",
        "Sector Concentration Limit",
        "concentration",
        "No single sector shall exceed 25% of total portfolio value. Sector classification follows GICS Level 1 taxonomy.",
        "percentage",
        0.25,
        "SEC",
        "2020-01-01",
    ),
    (
        "CR-003",
        "Risk Profile Suitability",
        "suitability",
        "Conservative accounts must maintain at least 40% in fixed income and cash. Moderate accounts must maintain at least 20% in fixed income.",
        "percentage",
        0.40,
        "FCA",
        "2019-06-15",
    ),
    (
        "CR-004",
        "ESG Mandate Compliance",
        "suitability",
        "Accounts with ESG mandates must not hold positions in excluded sectors or restricted securities as defined in the account metadata.",
        "boolean",
        1.0,
        "MiFID II",
        "2021-03-01",
    ),
    (
        "CR-005",
        "Large Transaction Reporting",
        "reporting",
        "Any single transaction exceeding $1,000,000 must be flagged for compliance review within 24 hours.",
        "absolute",
        1000000.0,
        "SEC",
        "2018-01-01",
    ),
    (
        "CR-006",
        "AML Threshold Monitoring",
        "aml",
        "Cash deposits or withdrawals exceeding $10,000 in aggregate within a 30-day period must trigger AML review.",
        "absolute",
        10000.0,
        "FinCEN",
        "2020-07-01",
    ),
]

GRAPH_SIMILARITIES = [
    ("ACC-001", "ACC-003", 0.82, "risk_profile"),
    ("ACC-001", "ACC-005", 0.78, "sector_exposure"),
    ("ACC-002", "ACC-004", 0.72, "sector_exposure"),
    ("ACC-003", "ACC-005", 0.80, "risk_profile"),
    ("ACC-004", "ACC-002", 0.88, "risk_profile"),
]

KNOWLEDGE_BASE_DOCS = [
    {
        "text": "Portfolio risk assessment methodology involves evaluating Value at Risk (VaR), Conditional VaR (CVaR), and stress testing across market scenarios. The standard approach uses historical simulation with a 95% confidence interval over a 10-day holding period. Risk factors include equity beta, interest rate duration, credit spread sensitivity, and currency exposure.",
        "metadata": {"source": "internal", "category": "risk_methodology", "doc_type": "policy"},
    },
    {
        "text": "Concentration risk limits are enforced at both the position and sector level. FCA guidelines require that no single equity position exceeds 10% of the portfolio for moderate-risk accounts. SEC Rule 15c3-1 provides additional capital requirements for concentrated positions. Passive breaches (through appreciation) must be reported within one business day.",
        "metadata": {
            "source": "regulatory",
            "category": "concentration_limits",
            "doc_type": "compliance",
        },
    },
    {
        "text": "ESG integration framework: Environmental, Social, and Governance factors are incorporated into investment analysis through negative screening (exclusion lists), positive screening (best-in-class), and thematic investing. ESG mandated accounts must exclude tobacco, firearms, gambling, and fossil fuel companies. Impact measurement uses SASB and GRI reporting standards.",
        "metadata": {"source": "internal", "category": "esg", "doc_type": "policy"},
    },
    {
        "text": "Fixed income risk analysis: Duration measures the sensitivity of bond prices to interest rate changes. A portfolio with a duration of 5 years will lose approximately 5% of its value for a 1% increase in interest rates. Convexity provides a second-order correction. Credit spread risk is measured using OAS (Option-Adjusted Spread) duration.",
        "metadata": {"source": "research", "category": "fixed_income", "doc_type": "analysis"},
    },
    {
        "text": "Market outlook Q1 2025: US equity markets face headwinds from elevated valuations (S&P 500 forward P/E of 21x) and potential Fed rate decisions. Technology sector continues to benefit from AI infrastructure spending. Fixed income offers attractive yields with 10Y Treasury at 4.3%. Emerging markets present value opportunities with improved fundamentals.",
        "metadata": {"source": "research", "category": "market_outlook", "doc_type": "analysis"},
    },
]


# ---------------------------------------------------------------------------
# PostgreSQL seed functions
# ---------------------------------------------------------------------------


def _has_postgis(pg_conn):
    """Check whether the PostGIS extension is active in the current database."""
    cur = pg_conn.cursor()
    try:
        cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'postgis'")
        result = cur.fetchone() is not None
        return result
    except Exception:
        pg_conn.rollback()
        return False
    finally:
        cur.close()


def seed_relationship_managers(pg_conn):
    """Insert relationship managers into PostgreSQL."""
    cur = pg_conn.cursor()
    for rm in RELATIONSHIP_MANAGERS:
        cur.execute(
            """INSERT INTO relationship_managers (rm_id, rm_name, region, team, email)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (rm_id) DO NOTHING""",
            rm,
        )
    pg_conn.commit()
    cur.close()
    print(f"    Seeded {len(RELATIONSHIP_MANAGERS)} relationship managers.")


def seed_rm_locations(pg_conn):
    """Set point locations for relationship managers (PostGIS or FLOAT fallback)."""
    has_postgis = _has_postgis(pg_conn)
    cur = pg_conn.cursor()
    for rm_id, lon, lat in RM_LOCATIONS:
        if has_postgis:
            cur.execute(
                """UPDATE relationship_managers
                   SET office_location = ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                   WHERE rm_id = %s""",
                (lon, lat, rm_id),
            )
        else:
            cur.execute(
                """UPDATE relationship_managers
                   SET office_latitude = %s, office_longitude = %s
                   WHERE rm_id = %s""",
                (lat, lon, rm_id),
            )
    pg_conn.commit()
    cur.close()
    print(f"    Set locations for {len(RM_LOCATIONS)} relationship managers.")


def seed_client_accounts(pg_conn):
    """Insert client accounts with JSONB metadata and locations (PostGIS or FLOAT fallback)."""
    has_postgis = _has_postgis(pg_conn)
    cur = pg_conn.cursor()
    for a in CLIENT_ACCOUNTS:
        if has_postgis:
            cur.execute(
                """INSERT INTO client_accounts
                       (account_id, client_name, account_type, risk_profile, aum,
                        relationship_manager, onboarded_date, metadata, location)
                   VALUES (%s, %s, %s, %s, %s, %s, %s::date, %s::jsonb,
                           ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                   ON CONFLICT (account_id) DO NOTHING""",
                (
                    a["account_id"],
                    a["client_name"],
                    a["account_type"],
                    a["risk_profile"],
                    a["aum"],
                    a["rm"],
                    a["date"],
                    json.dumps(a["metadata"]),
                    a["lon"],
                    a["lat"],
                ),
            )
        else:
            cur.execute(
                """INSERT INTO client_accounts
                       (account_id, client_name, account_type, risk_profile, aum,
                        relationship_manager, onboarded_date, metadata,
                        latitude, longitude)
                   VALUES (%s, %s, %s, %s, %s, %s, %s::date, %s::jsonb,
                           %s, %s)
                   ON CONFLICT (account_id) DO NOTHING""",
                (
                    a["account_id"],
                    a["client_name"],
                    a["account_type"],
                    a["risk_profile"],
                    a["aum"],
                    a["rm"],
                    a["date"],
                    json.dumps(a["metadata"]),
                    a["lat"],
                    a["lon"],
                ),
            )
    pg_conn.commit()
    cur.close()
    print(f"    Seeded {len(CLIENT_ACCOUNTS)} client accounts.")


def seed_portfolio_holdings(pg_conn):
    """Insert portfolio holdings into PostgreSQL."""
    cur = pg_conn.cursor()
    for h in PORTFOLIO_HOLDINGS:
        cur.execute(
            """INSERT INTO portfolio_holdings
                   (holding_id, account_id, asset_class, instrument_name, ticker,
                    quantity, current_value, purchase_price, purchase_date,
                    sector, region, risk_rating)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::date, %s, %s, %s)
               ON CONFLICT (holding_id) DO NOTHING""",
            h,
        )
    pg_conn.commit()
    cur.close()
    print(f"    Seeded {len(PORTFOLIO_HOLDINGS)} portfolio holdings.")


def seed_compliance_rules(pg_conn):
    """Insert compliance rules into PostgreSQL."""
    cur = pg_conn.cursor()
    for r in COMPLIANCE_RULES:
        cur.execute(
            """INSERT INTO compliance_rules
                   (rule_id, rule_name, category, description,
                    threshold_type, threshold_value, regulatory_body, effective_date)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s::date)
               ON CONFLICT (rule_id) DO NOTHING""",
            r,
        )
    pg_conn.commit()
    cur.close()
    print(f"    Seeded {len(COMPLIANCE_RULES)} compliance rules.")


# ---------------------------------------------------------------------------
# Neo4j seed functions
# ---------------------------------------------------------------------------


def seed_neo4j_nodes(neo4j_driver, pg_conn):
    """Create :Client and :Manager nodes in Neo4j from PostgreSQL data."""
    with neo4j_driver.session() as session:
        # Manager nodes
        for rm_id, rm_name, region, team, email in RELATIONSHIP_MANAGERS:
            session.run(
                """MERGE (m:Manager {rm_id: $rm_id})
                   SET m.rm_name = $rm_name, m.region = $region,
                       m.team = $team, m.email = $email""",
                rm_id=rm_id,
                rm_name=rm_name,
                region=region,
                team=team,
                email=email,
            )
        print(f"    Created {len(RELATIONSHIP_MANAGERS)} Manager nodes.")

        # Client nodes
        for a in CLIENT_ACCOUNTS:
            session.run(
                """MERGE (c:Client {account_id: $account_id})
                   SET c.client_name = $client_name,
                       c.account_type = $account_type,
                       c.risk_profile = $risk_profile,
                       c.aum = $aum""",
                account_id=a["account_id"],
                client_name=a["client_name"],
                account_type=a["account_type"],
                risk_profile=a["risk_profile"],
                aum=a["aum"],
            )
        print(f"    Created {len(CLIENT_ACCOUNTS)} Client nodes.")


def seed_neo4j_edges(neo4j_driver):
    """Create MANAGED_BY and SIMILAR_TO relationships in Neo4j."""
    rm_map = {rm[1]: rm[0] for rm in RELATIONSHIP_MANAGERS}

    with neo4j_driver.session() as session:
        # Client -> Manager edges
        for a in CLIENT_ACCOUNTS:
            rm_id = rm_map.get(a["rm"])
            if rm_id:
                session.run(
                    """MATCH (c:Client {account_id: $account_id})
                       MATCH (m:Manager {rm_id: $rm_id})
                       MERGE (c)-[:MANAGED_BY]->(m)""",
                    account_id=a["account_id"],
                    rm_id=rm_id,
                )
        print(f"    Created {len(CLIENT_ACCOUNTS)} MANAGED_BY edges.")

        # Similarity edges
        for src, tgt, score, sim_type in GRAPH_SIMILARITIES:
            session.run(
                """MATCH (a:Client {account_id: $src})
                   MATCH (b:Client {account_id: $tgt})
                   MERGE (a)-[r:SIMILAR_TO]->(b)
                   SET r.sim_score = $score, r.sim_type = $sim_type""",
                src=src,
                tgt=tgt,
                score=score,
                sim_type=sim_type,
            )
        print(f"    Created {len(GRAPH_SIMILARITIES)} SIMILAR_TO edges.")


# ---------------------------------------------------------------------------
# Qdrant seed functions
# ---------------------------------------------------------------------------


def seed_knowledge_base_qdrant(qdrant_client, embedding_model):
    """Embed and store knowledge base documents in Qdrant."""
    texts = [d["text"] for d in KNOWLEDGE_BASE_DOCS]
    embeddings = embedding_model.embed_documents(texts)

    points = []
    for _i, (doc, embedding) in enumerate(zip(KNOWLEDGE_BASE_DOCS, embeddings, strict=False)):
        point_id = str(uuid.uuid4())
        payload = {
            "text": doc["text"],
            **doc["metadata"],
        }
        points.append(PointStruct(id=point_id, vector=embedding, payload=payload))

    qdrant_client.upsert(collection_name="knowledge_base", points=points)
    print(f"    Seeded {len(points)} knowledge base documents into Qdrant.")


# ---------------------------------------------------------------------------
# Full seed orchestrator
# ---------------------------------------------------------------------------


def run_sprawl_seed(pg_conn, neo4j_driver, mongo_db, qdrant_client, embedding_model):
    """Run the complete sprawl seed data pipeline."""
    print("\n[1/7] Seeding relationship managers (Postgres)...")
    seed_relationship_managers(pg_conn)

    print("\n[2/7] Seeding RM locations (Postgres/PostGIS)...")
    seed_rm_locations(pg_conn)

    print("\n[3/7] Seeding client accounts (Postgres/PostGIS)...")
    seed_client_accounts(pg_conn)

    print("\n[4/7] Seeding portfolio holdings (Postgres)...")
    seed_portfolio_holdings(pg_conn)

    print("\n[5/7] Seeding compliance rules (Postgres)...")
    seed_compliance_rules(pg_conn)

    print("\n[6/7] Seeding graph nodes and edges (Neo4j)...")
    seed_neo4j_nodes(neo4j_driver, pg_conn)
    seed_neo4j_edges(neo4j_driver)

    print("\n[7/7] Seeding knowledge base (Qdrant)...")
    seed_knowledge_base_qdrant(qdrant_client, embedding_model)

    print("\nSprawl seed data complete!")


if __name__ == "__main__":
    from database.sprawl_connection import close_all, connect_all
    from langchain_huggingface import HuggingFaceEmbeddings

    embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    conns = connect_all()
    run_sprawl_seed(
        conns["pg_conn"],
        conns["neo4j_driver"],
        conns["mongo_db"],
        conns["qdrant_client"],
        embedding_model,
    )
    close_all(**conns)
