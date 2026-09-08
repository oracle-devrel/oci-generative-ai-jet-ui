"""Schema setup for the sprawl architecture: PostgreSQL, Neo4j, MongoDB, Qdrant."""

from qdrant_client.models import Distance, VectorParams

# ---------------------------------------------------------------------------
# PostgreSQL: relational tables + PostGIS + pgvector
# ---------------------------------------------------------------------------


def _postgis_available(pg_conn):
    """Check whether PostGIS is installed and usable."""
    cur = pg_conn.cursor()
    try:
        cur.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        pg_conn.commit()
        print("    Extension ready: postgis")
        return True
    except Exception as e:
        pg_conn.rollback()
        print(f"    PostGIS not available ({e}), falling back to FLOAT lat/lon columns.")
        return False
    finally:
        cur.close()


def setup_postgres(pg_conn):
    """Create all PostgreSQL tables, extensions, and indexes."""
    cur = pg_conn.cursor()

    # ---- Check PostGIS availability first ----
    has_postgis = _postgis_available(pg_conn)

    # ---- Remaining extensions ----
    extensions = [
        "CREATE EXTENSION IF NOT EXISTS vector",
        'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"',
    ]
    for ext in extensions:
        try:
            cur.execute(ext)
            pg_conn.commit()
            ext_name = ext.split("IF NOT EXISTS")[-1].strip().strip('"')
            print(f"    Extension ready: {ext_name}")
        except Exception as e:
            pg_conn.rollback()
            print(f"    Warning creating extension: {e}")

    # ---- Geometry column definitions (PostGIS vs FLOAT fallback) ----
    if has_postgis:
        client_location_col = "location geometry(Point, 4326)"
        rm_location_col = "office_location geometry(Point, 4326)"
    else:
        client_location_col = "latitude FLOAT,\n            longitude FLOAT"
        rm_location_col = "office_latitude FLOAT,\n            office_longitude FLOAT"

    # ---- Domain tables ----
    ddl_statements = [
        f"""CREATE TABLE IF NOT EXISTS client_accounts (
            account_id VARCHAR(50) PRIMARY KEY,
            client_name VARCHAR(255) NOT NULL,
            account_type VARCHAR(50),
            risk_profile VARCHAR(50),
            aum NUMERIC(15, 2),
            relationship_manager VARCHAR(255),
            onboarded_date DATE,
            status VARCHAR(20) DEFAULT 'active',
            metadata JSONB,
            {client_location_col}
        )""",
        """CREATE TABLE IF NOT EXISTS portfolio_holdings (
            holding_id VARCHAR(50) PRIMARY KEY,
            account_id VARCHAR(50) NOT NULL REFERENCES client_accounts(account_id),
            asset_class VARCHAR(50),
            instrument_name VARCHAR(255),
            ticker VARCHAR(20),
            quantity NUMERIC(15, 4),
            current_value NUMERIC(15, 2),
            purchase_price NUMERIC(15, 2),
            purchase_date DATE,
            sector VARCHAR(100),
            region VARCHAR(100),
            risk_rating NUMERIC(3, 1)
        )""",
        """CREATE TABLE IF NOT EXISTS compliance_rules (
            rule_id VARCHAR(50) PRIMARY KEY,
            rule_name VARCHAR(255),
            category VARCHAR(100),
            description TEXT,
            threshold_type VARCHAR(50),
            threshold_value NUMERIC(15, 4),
            regulatory_body VARCHAR(100),
            effective_date DATE,
            status VARCHAR(20) DEFAULT 'active'
        )""",
        """CREATE TABLE IF NOT EXISTS transactions (
            transaction_id VARCHAR(50) PRIMARY KEY,
            account_id VARCHAR(50) NOT NULL REFERENCES client_accounts(account_id),
            transaction_type VARCHAR(20),
            instrument_name VARCHAR(255),
            ticker VARCHAR(20),
            quantity NUMERIC(15, 4),
            price NUMERIC(15, 4),
            total_amount NUMERIC(15, 2),
            transaction_date TIMESTAMP,
            status VARCHAR(20)
        )""",
        f"""CREATE TABLE IF NOT EXISTS relationship_managers (
            rm_id VARCHAR(50) PRIMARY KEY,
            rm_name VARCHAR(255) NOT NULL,
            region VARCHAR(100),
            team VARCHAR(100),
            email VARCHAR(255),
            {rm_location_col}
        )""",
        # ---- Memory tables (relational) ----
        """CREATE TABLE IF NOT EXISTS conversational_memory (
            id VARCHAR(100) DEFAULT uuid_generate_v4()::text PRIMARY KEY,
            thread_id VARCHAR(100) NOT NULL,
            role VARCHAR(50) NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            summary_id VARCHAR(100) DEFAULT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS tool_log (
            id VARCHAR(100) DEFAULT uuid_generate_v4()::text PRIMARY KEY,
            thread_id VARCHAR(100) NOT NULL,
            tool_call_id VARCHAR(200) NOT NULL,
            tool_name VARCHAR(200) NOT NULL,
            tool_args TEXT,
            tool_output TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
    ]

    for ddl in ddl_statements:
        try:
            cur.execute(ddl)
            pg_conn.commit()
            # Extract table name from DDL
            table_name = ddl.split("TABLE IF NOT EXISTS")[-1].strip().split()[0].strip("(")
            print(f"    Table ready: {table_name}")
        except Exception as e:
            pg_conn.rollback()
            print(f"    Warning creating table: {e}")

    # ---- Indexes ----
    index_statements = [
        "CREATE INDEX IF NOT EXISTS idx_conv_thread_id ON conversational_memory(thread_id)",
        "CREATE INDEX IF NOT EXISTS idx_conv_timestamp ON conversational_memory(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_conv_summary ON conversational_memory(summary_id)",
        "CREATE INDEX IF NOT EXISTS idx_tool_log_thread ON tool_log(thread_id)",
        "CREATE INDEX IF NOT EXISTS idx_tool_log_call_id ON tool_log(tool_call_id)",
        "CREATE INDEX IF NOT EXISTS idx_holdings_account ON portfolio_holdings(account_id)",
        "CREATE INDEX IF NOT EXISTS idx_txn_account ON transactions(account_id)",
    ]
    if has_postgis:
        index_statements += [
            "CREATE INDEX IF NOT EXISTS idx_client_location ON client_accounts USING GIST(location)",
            "CREATE INDEX IF NOT EXISTS idx_rm_office_location ON relationship_managers USING GIST(office_location)",
        ]

    for idx_sql in index_statements:
        try:
            cur.execute(idx_sql)
            pg_conn.commit()
            idx_name = idx_sql.split("IF NOT EXISTS")[1].strip().split()[0]
            print(f"    Index ready: {idx_name}")
        except Exception as e:
            pg_conn.rollback()
            print(f"    Warning creating index: {e}")

    cur.close()
    print("  [Postgres] Schema setup complete.")


# ---------------------------------------------------------------------------
# Neo4j: constraints, indexes, node/relationship patterns
# ---------------------------------------------------------------------------


def setup_neo4j(neo4j_driver):
    """Create Neo4j constraints and indexes for the financial graph."""
    constraint_queries = [
        (
            "client_id_unique",
            "CREATE CONSTRAINT client_id_unique IF NOT EXISTS FOR (c:Client) REQUIRE c.account_id IS UNIQUE",
        ),
        (
            "manager_id_unique",
            "CREATE CONSTRAINT manager_id_unique IF NOT EXISTS FOR (m:Manager) REQUIRE m.rm_id IS UNIQUE",
        ),
    ]

    index_queries = [
        (
            "idx_client_name",
            "CREATE INDEX idx_client_name IF NOT EXISTS FOR (c:Client) ON (c.client_name)",
        ),
        (
            "idx_client_risk",
            "CREATE INDEX idx_client_risk IF NOT EXISTS FOR (c:Client) ON (c.risk_profile)",
        ),
        (
            "idx_manager_region",
            "CREATE INDEX idx_manager_region IF NOT EXISTS FOR (m:Manager) ON (m.region)",
        ),
    ]

    with neo4j_driver.session() as session:
        for name, cypher in constraint_queries:
            try:
                session.run(cypher)
                print(f"    Constraint ready: {name}")
            except Exception as e:
                print(f"    Warning creating constraint {name}: {e}")

        for name, cypher in index_queries:
            try:
                session.run(cypher)
                print(f"    Index ready: {name}")
            except Exception as e:
                print(f"    Warning creating index {name}: {e}")

    print("  [Neo4j] Schema setup complete.")


# ---------------------------------------------------------------------------
# MongoDB: collections and indexes
# ---------------------------------------------------------------------------


def setup_mongodb(mongo_db):
    """Create MongoDB collections with indexes."""
    # conversations collection
    try:
        if "conversations" not in mongo_db.list_collection_names():
            mongo_db.create_collection("conversations")
        conv = mongo_db["conversations"]
        conv.create_index([("thread_id", 1), ("timestamp", 1)])
        conv.create_index([("thread_id", 1), ("role", 1)])
        print("    Collection ready: conversations (with indexes)")
    except Exception as e:
        print(f"    Warning creating conversations collection: {e}")

    # tool_logs collection
    try:
        if "tool_logs" not in mongo_db.list_collection_names():
            mongo_db.create_collection("tool_logs")
        tl = mongo_db["tool_logs"]
        tl.create_index([("thread_id", 1), ("timestamp", 1)])
        tl.create_index([("tool_call_id", 1)])
        print("    Collection ready: tool_logs (with indexes)")
    except Exception as e:
        print(f"    Warning creating tool_logs collection: {e}")

    print("  [MongoDB] Schema setup complete.")


# ---------------------------------------------------------------------------
# Qdrant: vector collections
# ---------------------------------------------------------------------------


def setup_qdrant(qdrant_client):
    """Create Qdrant vector collections for memory stores."""
    collections = [
        ("knowledge_base", 768, Distance.COSINE),
        ("entity_memory", 768, Distance.COSINE),
        ("workflow_memory", 768, Distance.COSINE),
        ("toolbox_memory", 768, Distance.COSINE),
        ("summary_memory", 768, Distance.COSINE),
    ]

    existing = {c.name for c in qdrant_client.get_collections().collections}

    for name, size, distance in collections:
        try:
            if name in existing:
                print(f"    Collection already exists: {name}")
            else:
                qdrant_client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(size=size, distance=distance),
                )
                print(f"    Collection created: {name}")
        except Exception as e:
            print(f"    Warning creating collection {name}: {e}")

    print("  [Qdrant] Schema setup complete.")


# ---------------------------------------------------------------------------
# Full setup orchestrator
# ---------------------------------------------------------------------------


def run_full_sprawl_setup(pg_conn, neo4j_driver, mongo_db, qdrant_client):
    """Run the complete sprawl database setup pipeline."""
    print("\n[1/4] Setting up PostgreSQL (tables, indexes, extensions)...")
    setup_postgres(pg_conn)

    print("\n[2/4] Setting up Neo4j (constraints, indexes)...")
    setup_neo4j(neo4j_driver)

    print("\n[3/4] Setting up MongoDB (collections, indexes)...")
    setup_mongodb(mongo_db)

    print("\n[4/4] Setting up Qdrant (vector collections)...")
    setup_qdrant(qdrant_client)

    print("\nSprawl database setup complete!")


if __name__ == "__main__":
    from database.sprawl_connection import close_all, connect_all

    conns = connect_all()
    run_full_sprawl_setup(
        conns["pg_conn"],
        conns["neo4j_driver"],
        conns["mongo_db"],
        conns["qdrant_client"],
    )
    close_all(**conns)
