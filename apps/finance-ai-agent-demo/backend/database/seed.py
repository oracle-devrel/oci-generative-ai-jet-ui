"""Seed the database with synthetic financial services demo data."""

import json

from database.seed_expanded import (
    additional_accounts,
    additional_holdings,
    additional_kb_documents,
)


def seed_relationship_managers(conn):
    """Insert relationship managers."""
    rms = [
        ("RM-001", "Sarah Chen", "North America", "Wealth Management", "sarah.chen@firm.com"),
        ("RM-002", "James Morrison", "North America", "Institutional", "james.morrison@firm.com"),
        ("RM-003", "Priya Sharma", "APAC", "Wealth Management", "priya.sharma@firm.com"),
        ("RM-004", "Michael O'Brien", "EMEA", "Private Banking", "michael.obrien@firm.com"),
        ("RM-005", "Elena Rodriguez", "LATAM", "Corporate", "elena.rodriguez@firm.com"),
    ]
    with conn.cursor() as cur:
        for rm in rms:
            cur.execute(
                """MERGE INTO relationship_managers t
                   USING (SELECT :1 AS rm_id, :2 AS rm_name, :3 AS region,
                                 :4 AS team, :5 AS email FROM DUAL) s
                   ON (t.rm_id = s.rm_id)
                   WHEN NOT MATCHED THEN
                   INSERT (rm_id, rm_name, region, team, email)
                   VALUES (s.rm_id, s.rm_name, s.region, s.team, s.email)""",
                rm,
            )
    conn.commit()
    print(f"    Seeded {len(rms)} relationship managers.")


def seed_client_accounts(conn):
    """Insert client accounts with JSON metadata."""
    accounts = [
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
        },
        {
            "account_id": "ACC-003",
            "client_name": "Margaret Williams",
            "account_type": "individual",
            "risk_profile": "conservative",
            "aum": 1850000.00,
            "rm": "Sarah Chen",
            "date": "2020-01-10",
            "metadata": {
                "investment_preferences": {
                    "esg_mandate": False,
                    "max_single_position": 0.08,
                    "preferred_sectors": ["utilities", "healthcare", "consumer_staples"],
                    "excluded_sectors": ["crypto"],
                },
                "restricted_securities": [],
                "retirement_target_year": 2032,
                "income_requirement": "monthly",
            },
        },
        {
            "account_id": "ACC-004",
            "client_name": "TechVentures Inc.",
            "account_type": "corporate",
            "risk_profile": "aggressive",
            "aum": 15750000.00,
            "rm": "Priya Sharma",
            "date": "2021-04-20",
            "metadata": {
                "investment_preferences": {
                    "esg_mandate": True,
                    "max_single_position": 0.12,
                    "preferred_sectors": ["technology", "AI", "semiconductors"],
                    "excluded_sectors": ["fossil_fuels"],
                },
                "restricted_securities": ["XOM", "CVX"],
                "entity_type": "venture_fund",
            },
        },
        {
            "account_id": "ACC-005",
            "client_name": "Johnson Pension Fund",
            "account_type": "trust",
            "risk_profile": "conservative",
            "aum": 42000000.00,
            "rm": "Michael O'Brien",
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
        },
        {
            "account_id": "ACC-006",
            "client_name": "David Park",
            "account_type": "individual",
            "risk_profile": "moderate",
            "aum": 3100000.00,
            "rm": "Priya Sharma",
            "date": "2022-02-14",
            "metadata": {
                "investment_preferences": {
                    "esg_mandate": False,
                    "max_single_position": 0.10,
                    "preferred_sectors": ["technology", "financials"],
                    "excluded_sectors": [],
                },
                "restricted_securities": [],
                "tax_loss_harvesting": True,
            },
        },
        {
            "account_id": "ACC-007",
            "client_name": "GreenField Endowment",
            "account_type": "trust",
            "risk_profile": "moderate",
            "aum": 18200000.00,
            "rm": "Elena Rodriguez",
            "date": "2017-11-30",
            "metadata": {
                "investment_preferences": {
                    "esg_mandate": True,
                    "max_single_position": 0.07,
                    "preferred_sectors": ["renewables", "healthcare", "education"],
                    "excluded_sectors": ["fossil_fuels", "defense", "tobacco"],
                },
                "restricted_securities": ["LMT", "RTX", "BA"],
                "spending_rate": 0.045,
            },
        },
        {
            "account_id": "ACC-008",
            "client_name": "Nakamura Holdings",
            "account_type": "corporate",
            "risk_profile": "moderate",
            "aum": 9800000.00,
            "rm": "Priya Sharma",
            "date": "2020-07-15",
            "metadata": {
                "investment_preferences": {
                    "esg_mandate": False,
                    "max_single_position": 0.10,
                    "preferred_sectors": ["industrials", "technology", "materials"],
                    "excluded_sectors": [],
                },
                "restricted_securities": [],
                "currency_hedge": "JPY",
            },
        },
        {
            "account_id": "ACC-009",
            "client_name": "Rivera Family Office",
            "account_type": "individual",
            "risk_profile": "aggressive",
            "aum": 7500000.00,
            "rm": "Elena Rodriguez",
            "date": "2019-05-22",
            "metadata": {
                "investment_preferences": {
                    "esg_mandate": False,
                    "max_single_position": 0.15,
                    "preferred_sectors": ["real_estate", "private_equity", "crypto"],
                    "excluded_sectors": [],
                },
                "restricted_securities": [],
                "alternative_allocation_target": 0.40,
            },
        },
        {
            "account_id": "ACC-010",
            "client_name": "BlueStar Municipal Fund",
            "account_type": "trust",
            "risk_profile": "conservative",
            "aum": 35000000.00,
            "rm": "James Morrison",
            "date": "2016-03-01",
            "metadata": {
                "investment_preferences": {
                    "esg_mandate": True,
                    "max_single_position": 0.04,
                    "preferred_sectors": ["municipal_bonds", "treasuries"],
                    "excluded_sectors": ["equities"],
                },
                "restricted_securities": [],
                "tax_exempt": True,
                "state_preference": "California",
            },
        },
        {
            "account_id": "ACC-011",
            "client_name": "Chen & Associates",
            "account_type": "corporate",
            "risk_profile": "moderate",
            "aum": 5600000.00,
            "rm": "Sarah Chen",
            "date": "2021-08-10",
            "metadata": {
                "investment_preferences": {
                    "esg_mandate": True,
                    "max_single_position": 0.10,
                    "preferred_sectors": ["healthcare", "biotech"],
                    "excluded_sectors": ["tobacco"],
                },
                "restricted_securities": ["PM", "MO"],
            },
        },
        {
            "account_id": "ACC-012",
            "client_name": "Pacific Growth Partners",
            "account_type": "corporate",
            "risk_profile": "aggressive",
            "aum": 22000000.00,
            "rm": "Priya Sharma",
            "date": "2018-12-05",
            "metadata": {
                "investment_preferences": {
                    "esg_mandate": False,
                    "max_single_position": 0.20,
                    "preferred_sectors": ["technology", "emerging_markets"],
                    "excluded_sectors": [],
                },
                "restricted_securities": [],
                "leverage_ratio_max": 1.5,
            },
        },
        {
            "account_id": "ACC-013",
            "client_name": "Elizabeth Foster",
            "account_type": "individual",
            "risk_profile": "conservative",
            "aum": 980000.00,
            "rm": "Michael O'Brien",
            "date": "2023-01-20",
            "metadata": {
                "investment_preferences": {
                    "esg_mandate": False,
                    "max_single_position": 0.06,
                    "preferred_sectors": ["dividend_growth", "utilities"],
                    "excluded_sectors": ["crypto"],
                },
                "restricted_securities": [],
                "income_focus": True,
            },
        },
        {
            "account_id": "ACC-014",
            "client_name": "Atlas Infrastructure Fund",
            "account_type": "trust",
            "risk_profile": "moderate",
            "aum": 50000000.00,
            "rm": "James Morrison",
            "date": "2014-06-15",
            "metadata": {
                "investment_preferences": {
                    "esg_mandate": True,
                    "max_single_position": 0.05,
                    "preferred_sectors": ["infrastructure", "utilities", "real_estate"],
                    "excluded_sectors": ["tobacco", "gambling"],
                },
                "restricted_securities": [],
                "inflation_linked": True,
            },
        },
        {
            "account_id": "ACC-015",
            "client_name": "Kumar Wealth Management",
            "account_type": "individual",
            "risk_profile": "moderate",
            "aum": 6200000.00,
            "rm": "Priya Sharma",
            "date": "2020-10-01",
            "metadata": {
                "investment_preferences": {
                    "esg_mandate": True,
                    "max_single_position": 0.08,
                    "preferred_sectors": ["technology", "healthcare", "clean_energy"],
                    "excluded_sectors": ["defense"],
                },
                "restricted_securities": ["LMT", "NOC"],
                "nri_status": True,
            },
        },
    ]

    with conn.cursor() as cur:
        for a in accounts:
            cur.execute(
                """MERGE INTO client_accounts t
                   USING (SELECT :1 AS account_id, :2 AS client_name, :3 AS account_type,
                                 :4 AS risk_profile, :5 AS aum, :6 AS rm,
                                 :7 AS onboarded_dt, :8 AS metadata FROM DUAL) s
                   ON (t.account_id = s.account_id)
                   WHEN NOT MATCHED THEN
                   INSERT (account_id, client_name, account_type, risk_profile, aum,
                           relationship_manager, onboarded_date, metadata)
                   VALUES (s.account_id, s.client_name, s.account_type, s.risk_profile,
                           s.aum, s.rm, TO_DATE(s.onboarded_dt, 'YYYY-MM-DD'), s.metadata)""",
                (
                    a["account_id"],
                    a["client_name"],
                    a["account_type"],
                    a["risk_profile"],
                    a["aum"],
                    a["rm"],
                    a["date"],
                    json.dumps(a["metadata"]),
                ),
            )
    conn.commit()
    print(f"    Seeded {len(accounts)} client accounts.")


def seed_portfolio_holdings(conn):
    """Insert portfolio holdings across various asset classes."""
    holdings = [
        # Smith Family Trust (ACC-001) - moderate, ESG
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
        (
            "H-006",
            "ACC-001",
            "equity",
            "UnitedHealth Group",
            "UNH",
            200,
            105000.00,
            490.00,
            "2021-04-15",
            "Healthcare",
            "US",
            4.0,
        ),
        (
            "H-007",
            "ACC-001",
            "equity",
            "NVIDIA Corp.",
            "NVDA",
            1500,
            1125000.00,
            480.00,
            "2023-06-01",
            "Technology",
            "US",
            8.5,
        ),
        (
            "H-008",
            "ACC-001",
            "cash",
            "Money Market Fund",
            "MMKT",
            100000,
            100000.00,
            1.00,
            "2024-01-01",
            "Cash",
            "US",
            0.5,
        ),
        # Apex Capital Partners (ACC-002) - aggressive
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
        # Margaret Williams (ACC-003) - conservative
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
        # TechVentures (ACC-004) - aggressive, ESG
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
        # Johnson Pension Fund (ACC-005) - conservative, liability matching
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

    with conn.cursor() as cur:
        for h in holdings:
            cur.execute(
                """MERGE INTO portfolio_holdings t
                   USING (SELECT :1 AS holding_id, :2 AS account_id, :3 AS asset_class,
                                 :4 AS instrument_name, :5 AS ticker, :6 AS quantity,
                                 :7 AS current_value, :8 AS purchase_price,
                                 :9 AS purchase_dt, :10 AS sector, :11 AS region,
                                 :12 AS risk_rating FROM DUAL) s
                   ON (t.holding_id = s.holding_id)
                   WHEN NOT MATCHED THEN
                   INSERT (holding_id, account_id, asset_class, instrument_name, ticker,
                           quantity, current_value, purchase_price, purchase_date,
                           sector, region, risk_rating)
                   VALUES (s.holding_id, s.account_id, s.asset_class, s.instrument_name,
                           s.ticker, s.quantity, s.current_value, s.purchase_price,
                           TO_DATE(s.purchase_dt, 'YYYY-MM-DD'), s.sector, s.region,
                           s.risk_rating)""",
                h,
            )
    conn.commit()
    print(f"    Seeded {len(holdings)} portfolio holdings.")


def seed_compliance_rules(conn):
    """Insert compliance rules."""
    rules = [
        (
            "CR-001",
            "Single Position Concentration Limit",
            "concentration",
            "No single equity position shall exceed 10% of total portfolio value for moderate-risk accounts, or 15% for aggressive accounts. This rule applies to individual securities, not ETFs or mutual funds.",
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
            "Conservative accounts must maintain at least 40% in fixed income and cash. Moderate accounts must maintain at least 20% in fixed income. Aggressive accounts have no minimum fixed income requirement.",
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
        (
            "CR-007",
            "Derivatives Exposure Limit",
            "concentration",
            "Total notional derivatives exposure must not exceed 200% of account AUM for aggressive accounts and 50% for moderate or conservative accounts.",
            "percentage",
            2.0,
            "SEC",
            "2019-01-01",
        ),
        (
            "CR-008",
            "Liquidity Requirement",
            "suitability",
            "All accounts must maintain at least 5% in cash or cash-equivalent instruments for redemption requests.",
            "percentage",
            0.05,
            "FCA",
            "2020-01-01",
        ),
        (
            "CR-009",
            "International Exposure Limit",
            "concentration",
            "Emerging market exposure shall not exceed 15% of total portfolio for conservative accounts and 30% for moderate accounts.",
            "percentage",
            0.15,
            "SEC",
            "2021-01-01",
        ),
        (
            "CR-010",
            "Related Party Transaction Review",
            "reporting",
            "Any transaction involving a related party must be reviewed and approved by the compliance committee before execution.",
            "boolean",
            1.0,
            "SEC",
            "2018-06-01",
        ),
        (
            "CR-011",
            "Restricted Securities Check",
            "suitability",
            "Before any buy order, the system must verify the security is not on the account restricted list defined in account metadata.",
            "boolean",
            1.0,
            "FCA",
            "2020-01-01",
        ),
        (
            "CR-012",
            "Portfolio Turnover Limit",
            "reporting",
            "Annual portfolio turnover exceeding 200% for any account must be reviewed for excessive trading.",
            "percentage",
            2.0,
            "SEC",
            "2019-01-01",
        ),
        (
            "CR-013",
            "Cross-Border Investment Compliance",
            "reporting",
            "Investments in foreign securities must comply with local regulations and tax treaty requirements. FATCA reporting applies to US persons.",
            "boolean",
            1.0,
            "MiFID II",
            "2021-06-01",
        ),
        (
            "CR-014",
            "Leverage Limit",
            "concentration",
            "Total leverage (including margin) must not exceed 1.5x AUM for aggressive accounts. Leverage is prohibited for conservative accounts.",
            "percentage",
            1.5,
            "SEC",
            "2020-01-01",
        ),
        (
            "CR-015",
            "Concentration Risk Alert",
            "concentration",
            "If any single position grows to exceed 12% of portfolio through appreciation (passive breach), an alert must be generated within 1 business day.",
            "percentage",
            0.12,
            "FCA",
            "2022-01-01",
        ),
    ]

    with conn.cursor() as cur:
        for r in rules:
            cur.execute(
                """MERGE INTO compliance_rules t
                   USING (SELECT :1 AS rule_id, :2 AS rule_name, :3 AS category,
                                 :4 AS description, :5 AS threshold_type,
                                 :6 AS threshold_value, :7 AS regulatory_body,
                                 :8 AS effective_dt FROM DUAL) s
                   ON (t.rule_id = s.rule_id)
                   WHEN NOT MATCHED THEN
                   INSERT (rule_id, rule_name, category, description,
                           threshold_type, threshold_value, regulatory_body,
                           effective_date)
                   VALUES (s.rule_id, s.rule_name, s.category, s.description,
                           s.threshold_type, s.threshold_value, s.regulatory_body,
                           TO_DATE(s.effective_dt, 'YYYY-MM-DD'))""",
                r,
            )
    conn.commit()
    print(f"    Seeded {len(rules)} compliance rules.")


def seed_transactions(conn):
    """Insert sample transactions."""
    txns = [
        (
            "TXN-001",
            "ACC-001",
            "buy",
            "NVIDIA Corp.",
            "NVDA",
            500,
            480.25,
            240125.00,
            "2024-01-15 10:30:00",
            "completed",
        ),
        (
            "TXN-002",
            "ACC-001",
            "sell",
            "Apple Inc.",
            "AAPL",
            200,
            175.50,
            35100.00,
            "2024-01-20 14:15:00",
            "completed",
        ),
        (
            "TXN-003",
            "ACC-002",
            "buy",
            "Tesla Inc.",
            "TSLA",
            1000,
            248.75,
            248750.00,
            "2024-02-01 09:45:00",
            "completed",
        ),
        (
            "TXN-004",
            "ACC-002",
            "buy",
            "Bitcoin Trust",
            "GBTC",
            5000,
            45.00,
            225000.00,
            "2024-02-05 11:00:00",
            "completed",
        ),
        (
            "TXN-005",
            "ACC-003",
            "buy",
            "US Treasury 5Y",
            "UST5Y",
            100000,
            99.25,
            99250.00,
            "2024-01-10 13:30:00",
            "completed",
        ),
        (
            "TXN-006",
            "ACC-004",
            "buy",
            "AMD",
            "AMD",
            2000,
            152.30,
            304600.00,
            "2024-02-10 10:00:00",
            "completed",
        ),
        (
            "TXN-007",
            "ACC-005",
            "dividend",
            "NextEra Energy",
            "NEE",
            0,
            0.47,
            7050.00,
            "2024-01-25 00:00:00",
            "completed",
        ),
        (
            "TXN-008",
            "ACC-001",
            "buy",
            "UnitedHealth Group",
            "UNH",
            100,
            525.00,
            52500.00,
            "2024-02-15 15:20:00",
            "completed",
        ),
        (
            "TXN-009",
            "ACC-006",
            "buy",
            "Microsoft Corp.",
            "MSFT",
            300,
            410.00,
            123000.00,
            "2024-02-01 09:30:00",
            "completed",
        ),
        (
            "TXN-010",
            "ACC-007",
            "sell",
            "Lockheed Martin",
            "LMT",
            500,
            450.00,
            225000.00,
            "2024-01-05 10:00:00",
            "completed",
        ),
        (
            "TXN-011",
            "ACC-001",
            "fee",
            "Management Fee Q1",
            None,
            0,
            0,
            10625.00,
            "2024-03-31 00:00:00",
            "completed",
        ),
        (
            "TXN-012",
            "ACC-009",
            "buy",
            "Real Estate Fund",
            "VNQ",
            3000,
            88.50,
            265500.00,
            "2024-02-20 11:30:00",
            "completed",
        ),
    ]

    with conn.cursor() as cur:
        for t in txns:
            cur.execute(
                """MERGE INTO transactions tx
                   USING (SELECT :1 AS transaction_id, :2 AS account_id,
                                 :3 AS transaction_type, :4 AS instrument_name,
                                 :5 AS ticker, :6 AS quantity, :7 AS price,
                                 :8 AS total_amount, :9 AS txn_dt, :10 AS status FROM DUAL) s
                   ON (tx.transaction_id = s.transaction_id)
                   WHEN NOT MATCHED THEN
                   INSERT (transaction_id, account_id, transaction_type, instrument_name,
                           ticker, quantity, price, total_amount, transaction_date, status)
                   VALUES (s.transaction_id, s.account_id, s.transaction_type,
                           s.instrument_name, s.ticker, s.quantity, s.price,
                           s.total_amount,
                           TO_TIMESTAMP(s.txn_dt, 'YYYY-MM-DD HH24:MI:SS'), s.status)""",
                t,
            )
    conn.commit()
    print(f"    Seeded {len(txns)} transactions.")


def seed_graph_edges(conn):
    """Create relationship manager edges and account similarity edges."""
    # Client -> RM edges
    rm_map = {
        "Sarah Chen": "RM-001",
        "James Morrison": "RM-002",
        "Priya Sharma": "RM-003",
        "Michael O'Brien": "RM-004",
        "Elena Rodriguez": "RM-005",
    }

    with conn.cursor() as cur:
        cur.execute("SELECT account_id, relationship_manager FROM client_accounts")
        rows = cur.fetchall()

        for account_id, rm_name in rows:
            rm_id = rm_map.get(rm_name)
            if rm_id:
                cur.execute(
                    """MERGE INTO client_rm_edges t
                       USING (SELECT :1 AS account_id, :2 AS rm_id FROM DUAL) s
                       ON (t.account_id = s.account_id AND t.rm_id = s.rm_id)
                       WHEN NOT MATCHED THEN
                       INSERT (account_id, rm_id, relationship_start)
                       VALUES (s.account_id, s.rm_id, SYSDATE)""",
                    (account_id, rm_id),
                )

    conn.commit()
    print("    Seeded client-RM graph edges.")

    # Account similarity edges (pre-computed based on risk profile + sector overlap)
    similarities = [
        ("ACC-001", "ACC-006", 0.82, "risk_profile"),
        ("ACC-001", "ACC-011", 0.78, "sector_exposure"),
        ("ACC-001", "ACC-015", 0.85, "portfolio_overlap"),
        ("ACC-002", "ACC-004", 0.72, "sector_exposure"),
        ("ACC-002", "ACC-012", 0.88, "risk_profile"),
        ("ACC-002", "ACC-009", 0.75, "risk_profile"),
        ("ACC-003", "ACC-005", 0.80, "risk_profile"),
        ("ACC-003", "ACC-013", 0.90, "portfolio_overlap"),
        ("ACC-004", "ACC-012", 0.76, "sector_exposure"),
        ("ACC-005", "ACC-010", 0.85, "risk_profile"),
        ("ACC-005", "ACC-014", 0.82, "portfolio_overlap"),
        ("ACC-006", "ACC-015", 0.79, "sector_exposure"),
        ("ACC-007", "ACC-014", 0.74, "sector_exposure"),
        ("ACC-007", "ACC-011", 0.70, "portfolio_overlap"),
        ("ACC-008", "ACC-004", 0.68, "sector_exposure"),
    ]

    with conn.cursor() as cur:
        for s in similarities:
            cur.execute(
                """MERGE INTO account_similarities t
                   USING (SELECT :1 AS src, :2 AS tgt, :3 AS score, :4 AS stype FROM DUAL) s
                   ON (t.source_account_id = s.src AND t.target_account_id = s.tgt)
                   WHEN NOT MATCHED THEN
                   INSERT (source_account_id, target_account_id, sim_score, sim_type)
                   VALUES (s.src, s.tgt, s.score, s.stype)""",
                s,
            )
    conn.commit()
    print(f"    Seeded {len(similarities)} account similarity edges.")


def seed_knowledge_base(knowledge_base_vs):
    """Embed and store financial knowledge base documents."""
    documents = [
        {
            "text": "Portfolio risk assessment methodology involves evaluating Value at Risk (VaR), Conditional VaR (CVaR), and stress testing across market scenarios. The standard approach uses historical simulation with a 95% confidence interval over a 10-day holding period. Risk factors include equity beta, interest rate duration, credit spread sensitivity, and currency exposure.",
            "metadata": {
                "source": "internal",
                "category": "risk_methodology",
                "doc_type": "policy",
            },
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
            "metadata": {
                "source": "research",
                "category": "market_outlook",
                "doc_type": "analysis",
            },
        },
        {
            "text": "Portfolio hedging strategies include protective puts, collar strategies, and portfolio insurance. For systematic risk reduction, beta hedging using index futures is most capital efficient. Currency hedging for international positions can use forward contracts or currency-hedged ETFs. Tail risk hedging via out-of-the-money puts provides asymmetric protection.",
            "metadata": {"source": "research", "category": "hedging", "doc_type": "analysis"},
        },
        {
            "text": "AML (Anti-Money Laundering) compliance procedures: All accounts must undergo KYC (Know Your Customer) verification at onboarding. Transaction monitoring systems flag patterns including structuring, layering, and rapid movement of funds. CTRs (Currency Transaction Reports) are filed for cash transactions over $10,000. SARs (Suspicious Activity Reports) are filed within 30 days of detection.",
            "metadata": {"source": "regulatory", "category": "aml", "doc_type": "compliance"},
        },
        {
            "text": "Alternative investments allocation: For moderate-risk accounts, alternative investments (real estate, private equity, hedge funds, commodities) should not exceed 20% of total portfolio. Conservative accounts are limited to 10% alternatives. Due diligence requirements include manager track record, fee structure analysis, and liquidity terms review.",
            "metadata": {"source": "internal", "category": "alternatives", "doc_type": "policy"},
        },
        {
            "text": "Client suitability assessment framework: Investment recommendations must align with the client's stated risk profile, investment horizon, liquidity needs, and tax situation. Annual suitability reviews are mandatory. Changes in client circumstances (retirement, inheritance, divorce) trigger immediate portfolio review. MiFID II requires detailed suitability reporting.",
            "metadata": {
                "source": "regulatory",
                "category": "suitability",
                "doc_type": "compliance",
            },
        },
        {
            "text": "Sector analysis - Technology: The technology sector represents the largest weight in the S&P 500 at approximately 30%. Key sub-sectors include software (SaaS), semiconductors, cloud infrastructure, and AI/ML. Valuations are premium at 28x forward earnings. Growth is driven by enterprise digital transformation and AI adoption. Key risks include regulatory scrutiny and cyclical capex.",
            "metadata": {
                "source": "research",
                "category": "sector_analysis",
                "doc_type": "analysis",
            },
        },
        {
            "text": "Regulatory reporting requirements: SEC Form ADV must be filed annually. Form PF is required for large private fund advisers. MiFID II transaction reporting must include detailed client and instrument identifiers. FCA requires quarterly portfolio composition reports for regulated funds. FATCA reporting applies to foreign accounts held by US persons.",
            "metadata": {"source": "regulatory", "category": "reporting", "doc_type": "compliance"},
        },
        {
            "text": "Tax-loss harvesting strategy: Systematic identification of positions with unrealized losses for sale and reinvestment in similar (but not substantially identical) securities. Wash sale rule requires 30-day waiting period before repurchasing the same security. Harvested losses can offset capital gains and up to $3,000 of ordinary income annually.",
            "metadata": {"source": "internal", "category": "tax_strategy", "doc_type": "policy"},
        },
        {
            "text": "Dividend growth investing: Focuses on companies with consistent dividend increases over 10+ years. Key metrics include dividend yield, payout ratio, dividend growth rate, and free cash flow coverage. Sectors with strong dividend histories include utilities, consumer staples, healthcare, and financials. Dividend aristocrats (25+ years of increases) provide defensive characteristics.",
            "metadata": {
                "source": "research",
                "category": "income_investing",
                "doc_type": "analysis",
            },
        },
        {
            "text": "Emerging markets risk assessment: Key risks include currency volatility, political instability, regulatory uncertainty, and liquidity constraints. Country risk analysis uses sovereign credit ratings, GDP growth, current account balances, and political stability indices. Diversification across countries and sectors reduces idiosyncratic risk. Hard currency bonds provide currency risk mitigation.",
            "metadata": {
                "source": "research",
                "category": "emerging_markets",
                "doc_type": "analysis",
            },
        },
        {
            "text": "Portfolio rebalancing policy: Portfolios are rebalanced when asset allocation drifts beyond +/- 5% of target. Calendar-based rebalancing occurs quarterly. Threshold-based rebalancing triggers when any asset class exceeds its band. Tax-aware rebalancing prioritizes tax-lot selection to minimize capital gains. Transaction costs and market impact are considered for large portfolios.",
            "metadata": {"source": "internal", "category": "rebalancing", "doc_type": "policy"},
        },
    ]

    texts = [d["text"] for d in documents]
    metadatas = [d["metadata"] for d in documents]

    knowledge_base_vs.add_texts(texts=texts, metadatas=metadatas)
    print(f"    Seeded {len(documents)} knowledge base documents.")


def seed_expanded_accounts(conn):
    """Insert additional client accounts from seed_expanded.py."""
    with conn.cursor() as cur:
        for a in additional_accounts:
            cur.execute(
                """MERGE INTO client_accounts t
                   USING (SELECT :1 AS account_id, :2 AS client_name, :3 AS account_type,
                                 :4 AS risk_profile, :5 AS aum, :6 AS rm,
                                 :7 AS onboarded_dt, :8 AS metadata FROM DUAL) s
                   ON (t.account_id = s.account_id)
                   WHEN NOT MATCHED THEN
                   INSERT (account_id, client_name, account_type, risk_profile, aum,
                           relationship_manager, onboarded_date, metadata)
                   VALUES (s.account_id, s.client_name, s.account_type, s.risk_profile,
                           s.aum, s.rm, TO_DATE(s.onboarded_dt, 'YYYY-MM-DD'), s.metadata)""",
                (
                    a["account_id"],
                    a["client_name"],
                    a["account_type"],
                    a["risk_profile"],
                    a["aum"],
                    a["rm"],
                    a["date"],
                    json.dumps(a["metadata"]),
                ),
            )
    conn.commit()
    print(f"    Seeded {len(additional_accounts)} additional client accounts.")


def seed_expanded_holdings(conn):
    """Insert additional portfolio holdings from seed_expanded.py."""
    with conn.cursor() as cur:
        for h in additional_holdings:
            cur.execute(
                """MERGE INTO portfolio_holdings t
                   USING (SELECT :1 AS holding_id, :2 AS account_id, :3 AS asset_class,
                                 :4 AS instrument_name, :5 AS ticker, :6 AS quantity,
                                 :7 AS current_value, :8 AS purchase_price,
                                 :9 AS purchase_dt, :10 AS sector, :11 AS region,
                                 :12 AS risk_rating FROM DUAL) s
                   ON (t.holding_id = s.holding_id)
                   WHEN NOT MATCHED THEN
                   INSERT (holding_id, account_id, asset_class, instrument_name, ticker,
                           quantity, current_value, purchase_price, purchase_date,
                           sector, region, risk_rating)
                   VALUES (s.holding_id, s.account_id, s.asset_class, s.instrument_name,
                           s.ticker, s.quantity, s.current_value, s.purchase_price,
                           TO_DATE(s.purchase_dt, 'YYYY-MM-DD'), s.sector, s.region,
                           s.risk_rating)""",
                h,
            )
    conn.commit()
    print(f"    Seeded {len(additional_holdings)} additional portfolio holdings.")


def seed_expanded_knowledge_base(knowledge_base_vs):
    """Embed and store additional knowledge base documents from seed_expanded.py."""
    texts = [d["text"] for d in additional_kb_documents]
    metadatas = [d["metadata"] for d in additional_kb_documents]
    knowledge_base_vs.add_texts(texts=texts, metadatas=metadatas)
    print(f"    Seeded {len(additional_kb_documents)} additional knowledge base documents.")


def seed_expanded_graph_edges(conn):
    """Create similarity edges for the expanded accounts (ACC-016 to ACC-025)."""
    expanded_similarities = [
        ("ACC-016", "ACC-008", 0.79, "sector_exposure"),
        ("ACC-016", "ACC-011", 0.76, "risk_profile"),
        ("ACC-017", "ACC-009", 0.83, "risk_profile"),
        ("ACC-017", "ACC-002", 0.71, "sector_exposure"),
        ("ACC-018", "ACC-005", 0.87, "risk_profile"),
        ("ACC-018", "ACC-010", 0.82, "portfolio_overlap"),
        ("ACC-019", "ACC-002", 0.80, "risk_profile"),
        ("ACC-019", "ACC-012", 0.77, "sector_exposure"),
        ("ACC-020", "ACC-001", 0.84, "portfolio_overlap"),
        ("ACC-020", "ACC-015", 0.80, "sector_exposure"),
        ("ACC-021", "ACC-014", 0.86, "portfolio_overlap"),
        ("ACC-021", "ACC-007", 0.81, "sector_exposure"),
        ("ACC-022", "ACC-014", 0.73, "sector_exposure"),
        ("ACC-022", "ACC-008", 0.70, "risk_profile"),
        ("ACC-023", "ACC-003", 0.88, "risk_profile"),
        ("ACC-023", "ACC-013", 0.85, "portfolio_overlap"),
        ("ACC-024", "ACC-002", 0.74, "sector_exposure"),
        ("ACC-024", "ACC-019", 0.82, "risk_profile"),
        ("ACC-025", "ACC-007", 0.83, "portfolio_overlap"),
        ("ACC-025", "ACC-021", 0.79, "sector_exposure"),
    ]

    with conn.cursor() as cur:
        for s in expanded_similarities:
            cur.execute(
                """MERGE INTO account_similarities t
                   USING (SELECT :1 AS src, :2 AS tgt, :3 AS score, :4 AS stype FROM DUAL) s
                   ON (t.source_account_id = s.src AND t.target_account_id = s.tgt)
                   WHEN NOT MATCHED THEN
                   INSERT (source_account_id, target_account_id, sim_score, sim_type)
                   VALUES (s.src, s.tgt, s.score, s.stype)""",
                s,
            )
    conn.commit()
    print(f"    Seeded {len(expanded_similarities)} additional similarity edges.")


def seed_spatial_locations(conn):
    """Set geographic coordinates (SDO_GEOMETRY) for RMs and client accounts."""
    # Relationship manager office locations (lon, lat)
    rm_locations = [
        ("RM-001", -73.9857, 40.7484),  # New York
        ("RM-002", -87.6298, 41.8781),  # Chicago
        ("RM-003", 103.8198, 1.3521),  # Singapore
        ("RM-004", -0.1276, 51.5074),  # London
        ("RM-005", -46.6333, -23.5505),  # São Paulo
    ]

    # Client account locations (lon, lat)
    account_locations = [
        # North America
        ("ACC-001", -73.9857, 40.7484),  # New York
        ("ACC-002", -71.0589, 42.3601),  # Boston
        ("ACC-003", -122.4194, 37.7749),  # San Francisco
        ("ACC-004", -118.2437, 34.0522),  # Los Angeles
        ("ACC-005", -87.6298, 41.8781),  # Chicago
        ("ACC-006", -104.9903, 39.7392),  # Denver
        ("ACC-007", -79.3832, 43.6532),  # Toronto
        ("ACC-008", -80.1918, 25.7617),  # Miami
        # APAC
        ("ACC-009", 139.6917, 35.6895),  # Tokyo
        ("ACC-010", 114.1694, 22.3193),  # Hong Kong
        ("ACC-011", 151.2093, -33.8688),  # Sydney
        # EMEA
        ("ACC-012", -0.1276, 51.5074),  # London
        ("ACC-013", 8.5417, 47.3769),  # Zurich
        ("ACC-014", 8.6821, 50.1109),  # Frankfurt
        ("ACC-015", 55.2708, 25.2048),  # Dubai
        # Mixed (expanded accounts)
        ("ACC-016", -77.0369, 38.9072),  # Washington DC
        ("ACC-017", -43.1729, -22.9068),  # Rio de Janeiro
        ("ACC-018", -122.3321, 47.6062),  # Seattle
        ("ACC-019", 103.8198, 1.3521),  # Singapore
        ("ACC-020", -99.1332, 19.4326),  # Mexico City
        ("ACC-021", 10.7522, 59.9139),  # Oslo
        ("ACC-022", -96.7970, 32.7767),  # Dallas
        ("ACC-023", 121.4737, 31.2304),  # Shanghai
        ("ACC-024", -97.7431, 30.2672),  # Austin
        ("ACC-025", -71.0589, 42.3601),  # Boston
    ]

    with conn.cursor() as cur:
        for rm_id, lon, lat in rm_locations:
            cur.execute(
                """UPDATE relationship_managers
                   SET office_location = SDO_GEOMETRY(2001, 4326,
                       SDO_POINT_TYPE(:lon, :lat, NULL), NULL, NULL)
                   WHERE rm_id = :rm_id""",
                {"lon": lon, "lat": lat, "rm_id": rm_id},
            )

        for acc_id, lon, lat in account_locations:
            cur.execute(
                """UPDATE client_accounts
                   SET location = SDO_GEOMETRY(2001, 4326,
                       SDO_POINT_TYPE(:lon, :lat, NULL), NULL, NULL)
                   WHERE account_id = :acc_id""",
                {"lon": lon, "lat": lat, "acc_id": acc_id},
            )
    conn.commit()
    print(f"    Set locations for {len(rm_locations)} RMs and {len(account_locations)} accounts.")


def run_full_seed(conn, knowledge_base_vs):
    """Run the complete seed data pipeline."""
    print("\n[1/10] Seeding relationship managers...")
    seed_relationship_managers(conn)

    print("\n[2/10] Seeding client accounts...")
    seed_client_accounts(conn)

    print("\n[3/10] Seeding expanded client accounts...")
    seed_expanded_accounts(conn)

    print("\n[4/10] Seeding portfolio holdings...")
    seed_portfolio_holdings(conn)

    print("\n[5/10] Seeding expanded portfolio holdings...")
    seed_expanded_holdings(conn)

    print("\n[6/10] Seeding compliance rules...")
    seed_compliance_rules(conn)

    print("\n[7/10] Seeding transactions...")
    seed_transactions(conn)

    print("\n[8/10] Seeding knowledge base + graph edges...")
    seed_knowledge_base(knowledge_base_vs)
    seed_graph_edges(conn)

    print("\n[9/10] Seeding expanded knowledge base + graph edges...")
    seed_expanded_knowledge_base(knowledge_base_vs)
    seed_expanded_graph_edges(conn)

    print("\n[10/10] Seeding spatial locations...")
    seed_spatial_locations(conn)

    print("\nSeed data complete!")


if __name__ == "__main__":
    from config import EMBEDDING_MODEL_NAME
    from database.connection import connect_to_oracle
    from langchain_community.vectorstores.utils import DistanceStrategy
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_oracledb.vectorstores import OracleVS

    emb = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    conn = connect_to_oracle()
    kb_vs = OracleVS(
        client=conn,
        embedding_function=emb,
        table_name="KNOWLEDGE_BASE",
        distance_strategy=DistanceStrategy.COSINE,
    )
    run_full_seed(conn, kb_vs)
    conn.close()
