"""Database schema setup: tables, indexes, and property graph."""

import oracledb
from config import DB_CONFIG, ORACLE_ADMIN_PWD
from database.connection import connect_to_oracle, get_admin_connection


def create_user_if_needed():
    """Create the VECTOR user if it doesn't exist."""
    try:
        conn = get_admin_connection(ORACLE_ADMIN_PWD, dsn=DB_CONFIG["dsn"])
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM all_users WHERE username = :u",
                {"u": DB_CONFIG["user"].upper()},
            )
            if cur.fetchone()[0] == 0:
                cur.execute(
                    f"CREATE USER {DB_CONFIG['user']} IDENTIFIED BY {DB_CONFIG['password']}"
                )
                cur.execute(f"GRANT CONNECT, RESOURCE, UNLIMITED TABLESPACE TO {DB_CONFIG['user']}")
                cur.execute(f"GRANT CREATE PROPERTY GRAPH TO {DB_CONFIG['user']}")
                conn.commit()
                print(f"  User {DB_CONFIG['user']} created.")
            else:
                print(f"  User {DB_CONFIG['user']} already exists.")
        conn.close()
    except Exception as e:
        print(f"  Warning: Could not create user via SYSDBA: {e}")
        print("  Make sure the VECTOR user exists with required privileges.")


def _safe_execute(cur, sql, ignore_codes=None):
    """Execute SQL, ignoring specified ORA error codes."""
    ignore_codes = ignore_codes or []
    try:
        cur.execute(sql)
    except oracledb.DatabaseError as e:
        code = str(e)
        if any(f"ORA-{c}" in code for c in ignore_codes):
            pass
        else:
            raise


def create_tables(conn):
    """Create all relational and memory tables."""
    ddl_statements = [
        # ---- Domain tables ----
        """CREATE TABLE client_accounts (
            account_id VARCHAR2(50) PRIMARY KEY,
            client_name VARCHAR2(255) NOT NULL,
            account_type VARCHAR2(50),
            risk_profile VARCHAR2(50),
            aum NUMBER(15, 2),
            relationship_manager VARCHAR2(255),
            onboarded_date DATE,
            status VARCHAR2(20) DEFAULT 'active',
            metadata CLOB,
            location SDO_GEOMETRY
        ) TABLESPACE USERS""",
        """CREATE TABLE portfolio_holdings (
            holding_id VARCHAR2(50) PRIMARY KEY,
            account_id VARCHAR2(50) NOT NULL REFERENCES client_accounts(account_id),
            asset_class VARCHAR2(50),
            instrument_name VARCHAR2(255),
            ticker VARCHAR2(20),
            quantity NUMBER(15, 4),
            current_value NUMBER(15, 2),
            purchase_price NUMBER(15, 2),
            purchase_date DATE,
            sector VARCHAR2(100),
            region VARCHAR2(100),
            risk_rating NUMBER(3, 1)
        ) TABLESPACE USERS""",
        """CREATE TABLE compliance_rules (
            rule_id VARCHAR2(50) PRIMARY KEY,
            rule_name VARCHAR2(255),
            category VARCHAR2(100),
            description CLOB,
            threshold_type VARCHAR2(50),
            threshold_value NUMBER(15, 4),
            regulatory_body VARCHAR2(100),
            effective_date DATE,
            status VARCHAR2(20) DEFAULT 'active'
        ) TABLESPACE USERS""",
        """CREATE TABLE transactions (
            transaction_id VARCHAR2(50) PRIMARY KEY,
            account_id VARCHAR2(50) NOT NULL REFERENCES client_accounts(account_id),
            transaction_type VARCHAR2(20),
            instrument_name VARCHAR2(255),
            ticker VARCHAR2(20),
            quantity NUMBER(15, 4),
            price NUMBER(15, 4),
            total_amount NUMBER(15, 2),
            transaction_date TIMESTAMP,
            status VARCHAR2(20)
        ) TABLESPACE USERS""",
        """CREATE TABLE relationship_managers (
            rm_id VARCHAR2(50) PRIMARY KEY,
            rm_name VARCHAR2(255) NOT NULL,
            region VARCHAR2(100),
            team VARCHAR2(100),
            email VARCHAR2(255),
            office_location SDO_GEOMETRY
        ) TABLESPACE USERS""",
        # ---- Graph edge tables ----
        """CREATE TABLE client_rm_edges (
            account_id VARCHAR2(50) NOT NULL,
            rm_id VARCHAR2(50) NOT NULL,
            relationship_start DATE,
            CONSTRAINT pk_client_rm PRIMARY KEY (account_id, rm_id),
            CONSTRAINT fk_crm_account FOREIGN KEY (account_id) REFERENCES client_accounts(account_id),
            CONSTRAINT fk_crm_rm FOREIGN KEY (rm_id) REFERENCES relationship_managers(rm_id)
        ) TABLESPACE USERS""",
        """CREATE TABLE account_similarities (
            source_account_id VARCHAR2(50) NOT NULL,
            target_account_id VARCHAR2(50) NOT NULL,
            sim_score NUMBER(8, 6) NOT NULL,
            sim_type VARCHAR2(50),
            CONSTRAINT pk_account_sim PRIMARY KEY (source_account_id, target_account_id),
            CONSTRAINT fk_as_src FOREIGN KEY (source_account_id) REFERENCES client_accounts(account_id),
            CONSTRAINT fk_as_tgt FOREIGN KEY (target_account_id) REFERENCES client_accounts(account_id)
        ) TABLESPACE USERS""",
        # ---- Memory tables ----
        """CREATE TABLE CONVERSATIONAL_MEMORY (
            id VARCHAR2(100) DEFAULT SYS_GUID() PRIMARY KEY,
            thread_id VARCHAR2(100) NOT NULL,
            role VARCHAR2(50) NOT NULL,
            content CLOB NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata CLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            summary_id VARCHAR2(100) DEFAULT NULL
        )""",
        """CREATE TABLE TOOL_LOG (
            id VARCHAR2(100) DEFAULT SYS_GUID() PRIMARY KEY,
            thread_id VARCHAR2(100) NOT NULL,
            tool_call_id VARCHAR2(200) NOT NULL,
            tool_name VARCHAR2(200) NOT NULL,
            tool_args CLOB,
            tool_output CLOB,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
    ]

    index_statements = [
        "CREATE INDEX idx_conv_thread_id ON CONVERSATIONAL_MEMORY(thread_id)",
        "CREATE INDEX idx_conv_timestamp ON CONVERSATIONAL_MEMORY(timestamp)",
        "CREATE INDEX idx_tool_log_thread ON TOOL_LOG(thread_id)",
        "CREATE INDEX idx_holdings_account ON portfolio_holdings(account_id)",
        "CREATE INDEX idx_txn_account ON transactions(account_id)",
    ]

    with conn.cursor() as cur:
        for ddl in ddl_statements:
            table_name = ddl.split("TABLE")[1].strip().split()[0].strip("(")
            try:
                cur.execute(ddl)
                print(f"    Created table: {table_name}")
            except oracledb.DatabaseError as e:
                if "ORA-00955" in str(e):
                    print(f"    Table {table_name} already exists, skipping.")
                else:
                    raise

        for idx in index_statements:
            idx_name = idx.split("INDEX")[1].strip().split()[0]
            try:
                cur.execute(idx)
                print(f"    Created index: {idx_name}")
            except oracledb.DatabaseError as e:
                if "ORA-00955" in str(e) or "ORA-01408" in str(e):
                    pass
                else:
                    raise

    conn.commit()


def create_vector_stores(conn, embedding_model):
    """Create OracleVS vector-enabled tables and HNSW indexes."""
    from langchain_community.vectorstores.utils import DistanceStrategy
    from langchain_oracledb.vectorstores import OracleVS
    from langchain_oracledb.vectorstores.oraclevs import create_index

    stores = {}
    table_configs = [
        ("KNOWLEDGE_BASE", "kb_hnsw"),
        ("ENTITY_MEMORY", "entity_hnsw"),
        ("WORKFLOW_MEMORY", "workflow_hnsw"),
        ("TOOLBOX_MEMORY", "toolbox_hnsw"),
        ("SUMMARY_MEMORY", "summary_hnsw"),
    ]

    for table_name, idx_name in table_configs:
        vs = OracleVS(
            client=conn,
            embedding_function=embedding_model,
            table_name=table_name,
            distance_strategy=DistanceStrategy.COSINE,
        )
        stores[table_name] = vs
        print(f"    Vector store ready: {table_name}")

        try:
            create_index(
                client=conn,
                vector_store=vs,
                params={"idx_name": idx_name, "idx_type": "HNSW"},
            )
            print(f"    HNSW index created: {idx_name}")
        except Exception as e:
            if "ORA-00955" in str(e):
                print(f"    HNSW index {idx_name} already exists.")
            else:
                print(f"    Warning creating index {idx_name}: {e}")

    return stores


def create_text_index(conn):
    """Create Oracle Text full-text search index on KNOWLEDGE_BASE."""
    with conn.cursor() as cur:
        try:
            cur.execute(
                """CREATE INDEX kb_text_idx
                   ON KNOWLEDGE_BASE(text)
                   INDEXTYPE IS CTXSYS.CONTEXT
                   PARAMETERS ('SYNC (ON COMMIT)')"""
            )
            print("    Oracle Text index kb_text_idx created.")
        except oracledb.DatabaseError as e:
            if "ORA-00955" in str(e) or "DRG-10700" in str(e):
                print("    Oracle Text index kb_text_idx already exists.")
            else:
                print(f"    Warning creating text index: {e}")
    conn.commit()


def create_toolbox_text_index(conn):
    """Create Oracle Text index on TOOLBOX_MEMORY for hybrid tool search."""
    with conn.cursor() as cur:
        try:
            cur.execute(
                """CREATE INDEX toolbox_text_idx
                   ON TOOLBOX_MEMORY(text)
                   INDEXTYPE IS CTXSYS.CONTEXT
                   PARAMETERS ('SYNC (ON COMMIT)')"""
            )
            print("    Oracle Text index toolbox_text_idx created.")
        except oracledb.DatabaseError as e:
            if "ORA-00955" in str(e) or "DRG-10700" in str(e):
                print("    Oracle Text index toolbox_text_idx already exists.")
            else:
                print(f"    Warning creating toolbox text index: {e}")
    conn.commit()


def create_property_graph(conn):
    """Create the SQL Property Graph for financial relationships."""
    with conn.cursor() as cur:
        # Check if graph exists
        cur.execute(
            "SELECT COUNT(*) FROM user_property_graphs WHERE graph_name = 'FINANCIAL_GRAPH'"
        )
        if cur.fetchone()[0] > 0:
            try:
                cur.execute("DROP PROPERTY GRAPH financial_graph")
            except Exception:
                pass

        cur.execute(
            """
            CREATE PROPERTY GRAPH financial_graph
            VERTEX TABLES (
                client_accounts
                    KEY (account_id)
                    LABEL client
                    PROPERTIES (account_id, client_name, account_type, risk_profile, aum),
                relationship_managers
                    KEY (rm_id)
                    LABEL manager
                    PROPERTIES (rm_id, rm_name, region, team)
            )
            EDGE TABLES (
                client_rm_edges
                    KEY (account_id, rm_id)
                    SOURCE KEY (account_id) REFERENCES client_accounts (account_id)
                    DESTINATION KEY (rm_id) REFERENCES relationship_managers (rm_id)
                    LABEL managed_by,
                account_similarities
                    KEY (source_account_id, target_account_id)
                    SOURCE KEY (source_account_id) REFERENCES client_accounts (account_id)
                    DESTINATION KEY (target_account_id) REFERENCES client_accounts (account_id)
                    LABEL similar_to
                    PROPERTIES (sim_score, sim_type)
            )
        """
        )
    conn.commit()
    print("    Property graph FINANCIAL_GRAPH created.")


def create_spatial_indexes(conn):
    """Register spatial metadata and create R-tree spatial indexes."""
    with conn.cursor() as cur:
        # Ensure SDO_GEOMETRY columns exist (handles pre-existing tables)
        for ddl in [
            "ALTER TABLE client_accounts ADD (location SDO_GEOMETRY)",
            "ALTER TABLE relationship_managers ADD (office_location SDO_GEOMETRY)",
        ]:
            try:
                cur.execute(ddl)
                col = ddl.split("ADD")[1].strip().strip("()")
                print(f"    Added column: {col}")
            except oracledb.DatabaseError as e:
                if "ORA-01430" in str(e):
                    pass  # column already exists
                else:
                    raise
        conn.commit()

        # Register spatial metadata
        for tbl_name, col_name in [
            ("CLIENT_ACCOUNTS", "LOCATION"),
            ("RELATIONSHIP_MANAGERS", "OFFICE_LOCATION"),
        ]:
            try:
                cur.execute(
                    """INSERT INTO USER_SDO_GEOM_METADATA (TABLE_NAME, COLUMN_NAME, DIMINFO, SRID)
                       VALUES (:tbl_name, :col_name,
                               SDO_DIM_ARRAY(
                                   SDO_DIM_ELEMENT('LON', -180, 180, 0.005),
                                   SDO_DIM_ELEMENT('LAT', -90, 90, 0.005)
                               ), 4326)""",
                    {"tbl_name": tbl_name, "col_name": col_name},
                )
                print(f"    Spatial metadata registered: {tbl_name}.{col_name}")
            except oracledb.DatabaseError as e:
                if "ORA-13223" in str(e) or "unique constraint" in str(e).lower():
                    print(f"    Spatial metadata for {tbl_name}.{col_name} already exists.")
                else:
                    print(f"    Warning registering spatial metadata: {e}")
        conn.commit()

        # Create spatial indexes (drop FAILED indexes first)
        for idx_name, tbl, col in [
            ("idx_client_location", "client_accounts", "location"),
            ("idx_rm_office_location", "relationship_managers", "office_location"),
        ]:
            # Drop index if it exists in FAILED state
            _safe_execute(cur, f"DROP INDEX {idx_name}", ignore_codes=["01418", "00955"])
            try:
                cur.execute(
                    f"CREATE INDEX {idx_name} ON {tbl}({col}) " f"INDEXTYPE IS MDSYS.SPATIAL_INDEX"
                )
                print(f"    Spatial index created: {idx_name}")
            except oracledb.DatabaseError as e:
                if "ORA-00955" in str(e) or "ORA-29855" in str(e):
                    print(f"    Spatial index {idx_name} already exists.")
                else:
                    print(f"    Warning creating spatial index: {e}")
    conn.commit()


def run_full_setup(conn, embedding_model, skip_user_creation=False):
    """Run the complete database setup pipeline."""
    if not skip_user_creation:
        print("\n[1/7] Creating user...")
        create_user_if_needed()
    else:
        print("\n[1/7] User creation skipped (already done).")

    print("\n[2/7] Creating tables...")
    create_tables(conn)

    print("\n[3/7] Creating vector stores + HNSW indexes...")
    stores = create_vector_stores(conn, embedding_model)

    print("\n[4/7] Creating Oracle Text index (knowledge base)...")
    create_text_index(conn)

    print("\n[5/7] Creating Oracle Text index (toolbox)...")
    create_toolbox_text_index(conn)

    print("\n[6/7] Creating property graph...")
    create_property_graph(conn)

    print("\n[7/7] Creating spatial indexes...")
    create_spatial_indexes(conn)

    print("\nDatabase setup complete!")
    return stores


if __name__ == "__main__":
    from config import EMBEDDING_MODEL_NAME
    from langchain_huggingface import HuggingFaceEmbeddings

    emb = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    conn = connect_to_oracle()
    run_full_setup(conn, emb)
    conn.close()
