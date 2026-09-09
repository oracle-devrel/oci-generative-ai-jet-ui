#!/usr/bin/env python3
"""Setup the soccer database: tables, CSVs, indexes, views.

Targets the soccer-oracle Oracle AI Database Free container. Reads connection config
from .env. CSV files must already exist in DATA_DIR.
"""

import csv
import os
from pathlib import Path

import oracledb
from dotenv import load_dotenv

REPO = Path(__file__).resolve().parent.parent
load_dotenv(REPO / ".env")

DATA_DIR = REPO / "data"
DSN = os.environ["ORACLE_DSN"]
WC_USER = os.environ["ORACLE_USER"]
WC_PASS = os.environ["ORACLE_PASSWORD"]


def get_connection(user, password):
    return oracledb.connect(user=user, password=password, dsn=DSN)


def create_tables(cursor):
    """Create tables matching the CSV structures."""

    # Drop existing tables (ignore errors if they don't exist)
    for table in ["MATCH_RESULTS", "GOALSCORERS", "SHOOTOUTS", "WC2026_VENUES"]:
        try:
            cursor.execute(f"DROP TABLE {table} PURGE")
            print(f"  Dropped existing {table}")
        except oracledb.DatabaseError:
            pass

    cursor.execute("""
        CREATE TABLE MATCH_RESULTS (
            DATE_RW       DATE,
            HOME_TEAM     VARCHAR2(200),
            AWAY_TEAM     VARCHAR2(200),
            HOME_SCORE    NUMBER,
            AWAY_SCORE    NUMBER,
            TOURNAMENT    VARCHAR2(200),
            CITY          VARCHAR2(200),
            COUNTRY       VARCHAR2(200),
            NEUTRAL       VARCHAR2(10)
        )
    """)
    print("  Created MATCH_RESULTS")

    cursor.execute("""
        CREATE TABLE GOALSCORERS (
            DATE_RW       DATE,
            HOME_TEAM     VARCHAR2(200),
            AWAY_TEAM     VARCHAR2(200),
            TEAM          VARCHAR2(200),
            SCORER        VARCHAR2(200),
            MINUTE        VARCHAR2(20),
            OWN_GOAL      VARCHAR2(10),
            PENALTY       VARCHAR2(10)
        )
    """)
    print("  Created GOALSCORERS")

    cursor.execute("""
        CREATE TABLE SHOOTOUTS (
            DATE_RW        DATE,
            HOME_TEAM      VARCHAR2(200),
            AWAY_TEAM      VARCHAR2(200),
            WINNER         VARCHAR2(200),
            FIRST_SHOOTER  VARCHAR2(200)
        )
    """)
    print("  Created SHOOTOUTS")

    # Venues table from the guide
    cursor.execute("""
        CREATE TABLE WC2026_VENUES (
            VENUE_ID         NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            VENUE_NAME       VARCHAR2(200),
            CITY             VARCHAR2(100),
            COUNTRY          VARCHAR2(50),
            LATITUDE         NUMBER(10,6),
            LONGITUDE        NUMBER(10,6),
            ALTITUDE_METERS  NUMBER
        )
    """)
    print("  Created WC2026_VENUES")


def load_csv_with_date_conversion(cursor, filepath, table_name, ncols):
    """Load CSV with proper DATE conversion using TO_DATE."""
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)

        # Build insert with TO_DATE for first column
        col_placeholders = ["TO_DATE(:1, 'YYYY-MM-DD')"]
        for i in range(1, ncols):
            col_placeholders.append(f":{i+1}")
        sql = f"INSERT INTO {table_name} VALUES ({', '.join(col_placeholders)})"

        batch = []
        total = 0
        for row in reader:
            # Ensure correct number of columns
            while len(row) < ncols:
                row.append(None)
            row = row[:ncols]

            # Convert numeric fields for MATCH_RESULTS.
            # Future fixtures (unplayed 2026 World Cup matches) carry "NA"
            # in the score columns — store as NULL so they remain queryable
            # as scheduled matches without polluting analytics with zeros.
            if table_name == "MATCH_RESULTS":
                row[3] = int(row[3]) if row[3] and row[3] != "NA" else None
                row[4] = int(row[4]) if row[4] and row[4] != "NA" else None

            batch.append(row)
            if len(batch) >= 5000:
                cursor.executemany(sql, batch, batcherrors=True)
                errors = cursor.getbatcherrors()
                total += len(batch) - len(errors)
                if errors:
                    print(f"    {len(errors)} batch errors in {table_name}")
                batch = []

        if batch:
            cursor.executemany(sql, batch, batcherrors=True)
            errors = cursor.getbatcherrors()
            total += len(batch) - len(errors)
            if errors:
                print(f"    {len(errors)} batch errors in {table_name}")

    return total


def create_indexes(cursor):
    """Create indexes per the guide."""
    indexes = [
        ("idx_results_date", "MATCH_RESULTS(DATE_RW)"),
        ("idx_results_teams", "MATCH_RESULTS(HOME_TEAM, AWAY_TEAM)"),
        ("idx_goalscorers_scorer", "GOALSCORERS(SCORER)"),
    ]
    for idx_name, idx_def in indexes:
        try:
            cursor.execute(f"DROP INDEX {idx_name}")
        except oracledb.DatabaseError:
            pass
        cursor.execute(f"CREATE INDEX {idx_name} ON {idx_def}")
        print(f"  Created index {idx_name}")


def create_views(cursor):
    """Create analytical views per the guide."""

    cursor.execute("""
        CREATE OR REPLACE VIEW VW_COMPETITIVE_MATCHES
        (DATE_RW, HOME_TEAM, AWAY_TEAM, HOME_SCORE, AWAY_SCORE,
         TOURNAMENT, CITY, COUNTRY, NEUTRAL, WINNER) AS
        SELECT
            m.DATE_RW, m.HOME_TEAM, m.AWAY_TEAM, m.HOME_SCORE, m.AWAY_SCORE,
            m.TOURNAMENT, m.CITY, m.COUNTRY, m.NEUTRAL,
            CASE
                WHEN m.HOME_SCORE > m.AWAY_SCORE THEN m.HOME_TEAM
                WHEN m.AWAY_SCORE > m.HOME_SCORE THEN m.AWAY_TEAM
                ELSE 'Draw'
            END AS WINNER
        FROM MATCH_RESULTS m
        WHERE m.TOURNAMENT IN ('FIFA World Cup')
        AND m.DATE_RW >= DATE '1950-01-01'
    """)
    print("  Created VW_COMPETITIVE_MATCHES")

    cursor.execute("""
        CREATE OR REPLACE VIEW VW_TEAM_STATISTICS AS
        WITH team_matches AS (
            SELECT HOME_TEAM AS team,
                   CASE WHEN HOME_SCORE > AWAY_SCORE THEN 1 ELSE 0 END AS wins,
                   HOME_SCORE AS goals_for, AWAY_SCORE AS goals_against
            FROM VW_COMPETITIVE_MATCHES
            UNION ALL
            SELECT AWAY_TEAM AS team,
                   CASE WHEN AWAY_SCORE > HOME_SCORE THEN 1 ELSE 0 END AS wins,
                   AWAY_SCORE AS goals_for, HOME_SCORE AS goals_against
            FROM VW_COMPETITIVE_MATCHES
        )
        SELECT
            team,
            COUNT(*) AS total_matches,
            SUM(wins) AS total_wins,
            ROUND(SUM(wins) * 100.0 / COUNT(*), 2) AS win_percentage,
            SUM(goals_for) AS total_goals_scored,
            SUM(goals_for) - SUM(goals_against) AS goal_difference
        FROM team_matches
        GROUP BY team
    """)
    print("  Created VW_TEAM_STATISTICS")


def insert_venues(cursor):
    """Insert 2026 venue data per the guide."""
    cursor.execute("""
        INSERT INTO WC2026_VENUES (VENUE_NAME, CITY, COUNTRY, LATITUDE, LONGITUDE, ALTITUDE_METERS)
        VALUES ('Estadio Azteca', 'Mexico City', 'Mexico', 19.302969, -99.150635, 2200)
    """)
    cursor.execute("""
        INSERT INTO WC2026_VENUES (VENUE_NAME, CITY, COUNTRY, LATITUDE, LONGITUDE, ALTITUDE_METERS)
        VALUES ('SoFi Stadium', 'Los Angeles', 'USA', 33.953467, -118.339038, 30)
    """)
    cursor.execute("""
        INSERT INTO WC2026_VENUES (VENUE_NAME, CITY, COUNTRY, LATITUDE, LONGITUDE, ALTITUDE_METERS)
        VALUES ('MetLife Stadium', 'New York', 'USA', 40.813611, -74.074444, 3)
    """)
    print("  Inserted 3 venue records")


def main():
    print("=" * 60)
    print("World Cup 2026 Database Setup")
    print("=" * 60)

    conn = get_connection(WC_USER, WC_PASS)
    cursor = conn.cursor()

    print("\n1. Creating tables...")
    create_tables(cursor)
    conn.commit()

    print("\n2. Loading CSV data...")
    n = load_csv_with_date_conversion(
        cursor, os.path.join(DATA_DIR, "results.csv"), "MATCH_RESULTS", 9
    )
    conn.commit()
    print(f"  MATCH_RESULTS: {n} rows loaded")

    n = load_csv_with_date_conversion(
        cursor, os.path.join(DATA_DIR, "goalscorers.csv"), "GOALSCORERS", 8
    )
    conn.commit()
    print(f"  GOALSCORERS: {n} rows loaded")

    n = load_csv_with_date_conversion(
        cursor, os.path.join(DATA_DIR, "shootouts.csv"), "SHOOTOUTS", 5
    )
    conn.commit()
    print(f"  SHOOTOUTS: {n} rows loaded")

    print("\n3. Inserting venue data...")
    insert_venues(cursor)
    conn.commit()

    print("\n4. Creating indexes...")
    create_indexes(cursor)
    conn.commit()

    print("\n5. Creating analytical views...")
    create_views(cursor)
    conn.commit()

    # Verification
    print("\n6. Verification...")
    for table in ["MATCH_RESULTS", "GOALSCORERS", "SHOOTOUTS", "WC2026_VENUES"]:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table}: {count} rows")

    cursor.execute("SELECT COUNT(*) FROM VW_COMPETITIVE_MATCHES")
    print(f"  VW_COMPETITIVE_MATCHES: {cursor.fetchone()[0]} rows")

    cursor.execute("SELECT COUNT(*) FROM VW_TEAM_STATISTICS")
    print(f"  VW_TEAM_STATISTICS: {cursor.fetchone()[0]} teams")

    conn.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
