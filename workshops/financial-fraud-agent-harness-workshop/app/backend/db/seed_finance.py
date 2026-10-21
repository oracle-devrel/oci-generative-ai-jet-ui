"""Bank / AML schema + spatial setup + seed data + JSON duality views.

Mirrors the notebook's FINANCE seed, condensed into a single
re-runnable function. Idempotent: re-running drops and re-creates objects with
the same content.

The world is "Meridian Bank": 60 branches with SDO_GEOMETRY locations across
four regions (AMERICAS, EUROPE, MIDDLE_EAST, ASIA_PACIFIC), 2,000 customers
(2,650 accounts, ~3,000 cards, 140 merchants), ~23,600 transactions over the
last 90 days (including deliberate AML patterns: structuring, geographic
velocity, high-risk-corridor wires, rapid cash-out, large cash deposits),
900 loans and ~120 Suspicious Activity Reports (SAR_REPORTS — the
compliance-only table that drives the identity demo).

Alongside the core banking tables the schema carries the operational paperwork
an AML desk actually reads: SANCTIONS_SCREENINGS (watchlist name matches),
BENEFICIAL_OWNERS (who ultimately owns an SME/CORP customer), WIRE_MESSAGES
(SWIFT-style detail behind wire transactions), LOGIN_EVENTS (digital-banking
logins with SDO_GEOMETRY locations — the impossible-travel evidence),
KYC_DOCUMENTS (due-diligence paperwork and its expiry backlog), CASE_NOTES
(investigator narrative) and FX_RATES (daily USD rates).

Two generations of rows live side by side: the original "canonical" world
(customers 1-200, accounts 1-250, transactions 1-1199, 15 SARs) is drawn from
``random.seed(42)`` exactly as it always was, so every value quoted in the
workshop docs (customer 7 = Ravi Hill structuring, the $18,372.61 exposure,
txn 1125/1126, ...) keeps holding; the augmented world is drawn from a second,
independent stream (``EXT_SEED``) and appended after it. Re-running therefore
never moves the documented examples.

Idempotent: re-running drops and re-creates everything from scratch.
"""

from __future__ import annotations

import datetime as _dt
import random

import oracledb


SCHEMA = "FINANCE"

REGIONS = ["AMERICAS", "EUROPE", "MIDDLE_EAST", "ASIA_PACIFIC"]

# Flag reasons the AML rules write onto transactions (used by the agent's
# "which transactions were flagged and why" material).
FLAG_REASONS = [
    "STRUCTURING",
    "GEO_VELOCITY",
    "HIGH_RISK_COUNTRY",
    "RAPID_CASH_OUT",
    "LARGE_CASH_DEPOSIT",
]


# ---------- DDL --------------------------------------------------------------
DDL = [
    """CREATE TABLE branches (
         branch_id      NUMBER(10) PRIMARY KEY,
         branch_code    VARCHAR2(8) UNIQUE NOT NULL,
         name           VARCHAR2(120) NOT NULL,
         city           VARCHAR2(60),
         country        VARCHAR2(60),
         region         VARCHAR2(20) NOT NULL,
         latitude       NUMBER(10,6),
         longitude      NUMBER(10,6),
         location       SDO_GEOMETRY,
         opened_year    NUMBER(4)
       )""",
    """CREATE TABLE customers (
         customer_id    NUMBER(10) PRIMARY KEY,
         full_name      VARCHAR2(120) NOT NULL,
         ssn            VARCHAR2(11) UNIQUE NOT NULL,
         country        VARCHAR2(60),
         segment        VARCHAR2(20) NOT NULL,
         risk_rating    NUMBER(3)
       )""",
    """CREATE TABLE accounts (
         account_id     NUMBER(10) PRIMARY KEY,
         customer_id    NUMBER(10) NOT NULL REFERENCES customers(customer_id),
         branch_id      NUMBER(10) NOT NULL REFERENCES branches(branch_id),
         account_type   VARCHAR2(20) NOT NULL,
         currency       VARCHAR2(3) NOT NULL,
         balance_cents  NUMBER(15),
         opened_ts      TIMESTAMP,
         status         VARCHAR2(20) NOT NULL
       )""",
    """CREATE TABLE cards (
         card_id        NUMBER(10) PRIMARY KEY,
         account_id     NUMBER(10) NOT NULL REFERENCES accounts(account_id),
         card_type      VARCHAR2(20) NOT NULL,
         card_number    VARCHAR2(16) UNIQUE NOT NULL,
         issued_ts      TIMESTAMP,
         status         VARCHAR2(20) NOT NULL,
         daily_limit_cents NUMBER(15)
       )""",
    """CREATE TABLE merchants (
         merchant_id    NUMBER(10) PRIMARY KEY,
         name           VARCHAR2(120) NOT NULL,
         mcc_code       VARCHAR2(4),
         category       VARCHAR2(60),
         country        VARCHAR2(60),
         region         VARCHAR2(20) NOT NULL,
         latitude       NUMBER(10,6),
         longitude      NUMBER(10,6),
         location       SDO_GEOMETRY
       )""",
    """CREATE TABLE transactions (
         txn_id         NUMBER(10) PRIMARY KEY,
         account_id     NUMBER(10) NOT NULL REFERENCES accounts(account_id),
         merchant_id    NUMBER(10) REFERENCES merchants(merchant_id),
         txn_ts         TIMESTAMP,
         amount_cents   NUMBER(15),
         currency       VARCHAR2(3) NOT NULL,
         channel        VARCHAR2(20) NOT NULL,
         txn_type       VARCHAR2(20) NOT NULL,
         status         VARCHAR2(20) NOT NULL,
         flag_reason    VARCHAR2(60),
         region         VARCHAR2(20) NOT NULL
       )""",
    """CREATE TABLE loans (
         loan_id        NUMBER(10) PRIMARY KEY,
         customer_id    NUMBER(10) NOT NULL REFERENCES customers(customer_id),
         branch_id      NUMBER(10) NOT NULL REFERENCES branches(branch_id),
         loan_type      VARCHAR2(20) NOT NULL,
         amount_cents   NUMBER(15),
         rate_bp        NUMBER(5),
         term_months    NUMBER(4),
         status         VARCHAR2(20) NOT NULL
       )""",
    """CREATE TABLE sar_reports (
         sar_id         NUMBER(10) PRIMARY KEY,
         customer_id    NUMBER(10) NOT NULL REFERENCES customers(customer_id),
         filed_ts       TIMESTAMP,
         reason_code    VARCHAR2(30) NOT NULL,
         narrative      VARCHAR2(1000),
         status         VARCHAR2(20) NOT NULL
       )""",
    """CREATE TABLE sanctions_screenings (
         screening_id   NUMBER(10) PRIMARY KEY,
         customer_id    NUMBER(10) NOT NULL REFERENCES customers(customer_id),
         screened_ts    TIMESTAMP,
         list_type      VARCHAR2(20) NOT NULL,
         matched_name   VARCHAR2(120),
         match_score    NUMBER(4),
         disposition    VARCHAR2(20) NOT NULL,
         reviewer       VARCHAR2(60),
         note           VARCHAR2(300)
       )""",
    """CREATE TABLE beneficial_owners (
         ownership_id      NUMBER(10) PRIMARY KEY,
         company_id        NUMBER(10) NOT NULL REFERENCES customers(customer_id),
         owner_name        VARCHAR2(120) NOT NULL,
         owner_customer_id NUMBER(10) REFERENCES customers(customer_id),
         ownership_pct     NUMBER(5,2) NOT NULL,
         layer             NUMBER(2) NOT NULL,
         jurisdiction      VARCHAR2(60),
         verified_ts       TIMESTAMP
       )""",
    """CREATE TABLE wire_messages (
         message_id          NUMBER(10) PRIMARY KEY,
         txn_id              NUMBER(10) NOT NULL REFERENCES transactions(txn_id),
         sender_bic          VARCHAR2(11),
         receiver_bic        VARCHAR2(11),
         ordering_name       VARCHAR2(120),
         beneficiary_name    VARCHAR2(120),
         beneficiary_country VARCHAR2(60),
         purpose_code        VARCHAR2(10),
         remittance_info     VARCHAR2(200),
         sent_ts             TIMESTAMP
       )""",
    """CREATE TABLE login_events (
         event_id     NUMBER(10) PRIMARY KEY,
         customer_id  NUMBER(10) NOT NULL REFERENCES customers(customer_id),
         event_ts     TIMESTAMP,
         city         VARCHAR2(60),
         country      VARCHAR2(60),
         region       VARCHAR2(20) NOT NULL,
         latitude     NUMBER(10,6),
         longitude    NUMBER(10,6),
         location     SDO_GEOMETRY,
         ip_address   VARCHAR2(45),
         device_id    VARCHAR2(40),
         channel      VARCHAR2(20) NOT NULL,
         outcome      VARCHAR2(20) NOT NULL
       )""",
    """CREATE TABLE kyc_documents (
         document_id    NUMBER(10) PRIMARY KEY,
         customer_id    NUMBER(10) NOT NULL REFERENCES customers(customer_id),
         doc_type       VARCHAR2(30) NOT NULL,
         issued_country VARCHAR2(60),
         received_ts    TIMESTAMP,
         expires_ts     TIMESTAMP,
         status         VARCHAR2(20) NOT NULL,
         verified_by    VARCHAR2(60)
       )""",
    """CREATE TABLE case_notes (
         note_id        NUMBER(10) PRIMARY KEY,
         customer_id    NUMBER(10) NOT NULL REFERENCES customers(customer_id),
         sar_id         NUMBER(10) REFERENCES sar_reports(sar_id),
         author         VARCHAR2(60) NOT NULL,
         note_ts        TIMESTAMP,
         classification VARCHAR2(20) NOT NULL,
         note_text      VARCHAR2(1000)
       )""",
    """CREATE TABLE fx_rates (
         rate_date  DATE NOT NULL,
         currency   VARCHAR2(3) NOT NULL,
         usd_rate   NUMBER(12,6) NOT NULL,
         CONSTRAINT fx_rates_pk PRIMARY KEY (rate_date, currency)
       )""",
    "COMMENT ON COLUMN transactions.amount_cents IS 'Transaction amount in USD CENTS, never dollars; divide by 100 for dollars.'",
    "COMMENT ON COLUMN transactions.region IS 'Denormalized home-branch region of the transacting account; drives the DDS row policy.'",
    "COMMENT ON COLUMN transactions.flag_reason IS 'Reason the AML rules flagged or blocked this transaction (STRUCTURING, GEO_VELOCITY, HIGH_RISK_COUNTRY, RAPID_CASH_OUT, LARGE_CASH_DEPOSIT).'",
    "COMMENT ON COLUMN accounts.balance_cents IS 'Current balance in USD CENTS, never dollars; divide by 100 for dollars.'",
    "COMMENT ON COLUMN customers.risk_rating IS '1-100 customer risk score; higher means riskier.'",
    "COMMENT ON TABLE transactions IS 'Card/account transactions; status FLAGGED or BLOCKED indicates an AML rule hit with flag_reason set.'",
    "COMMENT ON TABLE sar_reports IS 'Suspicious Activity Reports; compliance-only, restricted by the DDS policies.'",
    "COMMENT ON TABLE branches IS 'Bank branches worldwide; location is SDO_GEOMETRY (WGS84, SRID 8307).'",
    "COMMENT ON TABLE merchants IS 'Merchants where card transactions occur; location is SDO_GEOMETRY (WGS84, SRID 8307).'",
    "COMMENT ON TABLE sanctions_screenings IS 'Watchlist screening results: OFAC / EU / UN / PEP / adverse-media name matches with a reviewer disposition.'",
    "COMMENT ON COLUMN sanctions_screenings.match_score IS 'Name-similarity score 0-100 against the list entry; 85 and above is a true-positive candidate.'",
    "COMMENT ON COLUMN sanctions_screenings.disposition IS 'CLEARED (false positive), ESCALATED (true positive, feeds a SAR), PENDING (awaiting reviewer).'",
    "COMMENT ON TABLE beneficial_owners IS 'Declared ownership of SME/CORP customers: who ultimately owns the entity, per layer (1 = direct holder).'",
    "COMMENT ON COLUMN beneficial_owners.layer IS 'Ownership depth: 1 = direct holder of the company, 2 = holder of the layer-1 holder (the layering examiners look for).'",
    "COMMENT ON TABLE wire_messages IS 'SWIFT-style payment detail behind WIRE transactions: BICs, ordering and beneficiary parties, purpose code.'",
    "COMMENT ON COLUMN wire_messages.txn_id IS 'The WIRE transaction this message belongs to; join to TRANSACTIONS.TXN_ID.'",
    "COMMENT ON COLUMN wire_messages.beneficiary_country IS 'Country of the party receiving the funds: the counterparty for WIRE_OUT, the customer for WIRE_IN.'",
    "COMMENT ON COLUMN transactions.txn_type IS 'PURCHASE, CARD_PAYMENT, WITHDRAWAL, DEPOSIT, TRANSFER, WIRE_IN or WIRE_OUT. WIRE_IN/WIRE_OUT rows have a matching row in WIRE_MESSAGES (join on TXN_ID).'",
    "COMMENT ON COLUMN wire_messages.purpose_code IS 'ISO 20022 style purpose code: TRAD, SALA, GDDS, INTC, CASH, DIVI, LOAN or SUPP.'",
    "COMMENT ON TABLE login_events IS 'Digital-banking login attempts with city and SDO_GEOMETRY location; the evidence behind impossible-travel cases.'",
    "COMMENT ON COLUMN login_events.outcome IS 'SUCCESS, FAILED_CHALLENGE (wrong OTP), BLOCKED (risk engine) or MFA_TIMEOUT.'",
    "COMMENT ON TABLE kyc_documents IS 'Customer due-diligence paperwork with expiry dates; EXPIRED and PENDING rows are the remediation backlog.'",
    "COMMENT ON TABLE case_notes IS 'Investigator notes on a customer or a SAR - the narrative trail behind SAR_REPORTS.'",
    "COMMENT ON TABLE fx_rates IS 'Daily FX rates as USD per 1 unit of currency. NOTE: accounts.balance_cents and transactions.amount_cents are already USD cents.'",
]

SPATIAL = [
    "DELETE FROM USER_SDO_GEOM_METADATA WHERE table_name IN ('BRANCHES', 'MERCHANTS', 'LOGIN_EVENTS')",
    """INSERT INTO USER_SDO_GEOM_METADATA (table_name, column_name, diminfo, srid)
       VALUES ('BRANCHES', 'LOCATION',
               SDO_DIM_ARRAY(
                 SDO_DIM_ELEMENT('LON', -180, 180, 0.005),
                 SDO_DIM_ELEMENT('LAT',  -90,  90, 0.005)
               ), 8307)""",
    """INSERT INTO USER_SDO_GEOM_METADATA (table_name, column_name, diminfo, srid)
       VALUES ('MERCHANTS', 'LOCATION',
               SDO_DIM_ARRAY(
                 SDO_DIM_ELEMENT('LON', -180, 180, 0.005),
                 SDO_DIM_ELEMENT('LAT',  -90,  90, 0.005)
               ), 8307)""",
    """INSERT INTO USER_SDO_GEOM_METADATA (table_name, column_name, diminfo, srid)
       VALUES ('LOGIN_EVENTS', 'LOCATION',
               SDO_DIM_ARRAY(
                 SDO_DIM_ELEMENT('LON', -180, 180, 0.005),
                 SDO_DIM_ELEMENT('LAT',  -90,  90, 0.005)
               ), 8307)""",
    "CREATE INDEX branches_loc_sx  ON branches(location) INDEXTYPE IS MDSYS.SPATIAL_INDEX_V2",
    "CREATE INDEX merchants_loc_sx ON merchants(location) INDEXTYPE IS MDSYS.SPATIAL_INDEX_V2",
    "CREATE INDEX login_events_loc_sx ON login_events(location) INDEXTYPE IS MDSYS.SPATIAL_INDEX_V2",
]

# ---------- Reference data ---------------------------------------------------
# (branch_id, branch_code, name, city, country, region, latitude, longitude, opened_year)
BRANCHES = [
    # AMERICAS
    (1,  "NYC", "Wall Street",          "New York",     "USA",          "AMERICAS",     40.706100,  -74.008900, 1998),
    (2,  "MIA", "Brickell Avenue",       "Miami",        "USA",          "AMERICAS",     25.761700,  -80.191800, 2003),
    (3,  "CHI", "LaSalle Street",        "Chicago",      "USA",          "AMERICAS",     41.878100,  -87.629800, 1995),
    (4,  "DAL", "Main Street",           "Dallas",       "USA",          "AMERICAS",     32.776700,  -96.797000, 2008),
    (5,  "LAX", "Wilshire Boulevard",    "Los Angeles",  "USA",          "AMERICAS",     34.052200, -118.243700, 1991),
    (6,  "SEA", "Pike Street",           "Seattle",      "USA",          "AMERICAS",     47.606200, -122.332100, 2011),
    (7,  "TOR", "Bay Street",            "Toronto",      "Canada",       "AMERICAS",     43.653200,  -79.383200, 1999),
    (8,  "MEX", "Paseo de la Reforma",   "Mexico City",  "Mexico",       "AMERICAS",     19.432600,  -99.133200, 2005),
    (9,  "SAO", "Avenida Paulista",      "Sao Paulo",    "Brazil",       "AMERICAS",    -23.561400,  -46.655900, 2010),
    # EUROPE
    (10, "LON", "Canary Wharf",          "London",       "UK",           "EUROPE",       51.504800,   -0.023500, 1997),
    (11, "PAR", "Opera",                 "Paris",        "France",       "EUROPE",       48.870600,    2.335300, 2001),
    (12, "BER", "Kurfurstendamm",        "Berlin",       "Germany",      "EUROPE",       52.520000,   13.405000, 2006),
    (13, "AMS", "Herengracht",           "Amsterdam",    "Netherlands",  "EUROPE",       52.367600,    4.904100, 1994),
    (14, "ZRH", "Bahnhofstrasse",        "Zurich",       "Switzerland",  "EUROPE",       47.376900,    8.541700, 1993),
    (15, "MAD", "Gran Via",              "Madrid",       "Spain",        "EUROPE",       40.416800,   -3.703800, 2002),
    (16, "MIL", "Via Monte Napoleone",   "Milan",        "Italy",        "EUROPE",       45.464200,    9.190000, 2004),
    (17, "DUB", "IFSC",                  "Dublin",       "Ireland",      "EUROPE",       53.349800,   -6.260300, 2012),
    # MIDDLE_EAST
    (18, "DXB", "DIFC",                  "Dubai",        "UAE",          "MIDDLE_EAST",  25.204800,   55.270800, 2007),
    (19, "TLV", "Rothschild Boulevard",  "Tel Aviv",     "Israel",       "MIDDLE_EAST",  32.085300,   34.781800, 2013),
    (20, "RUH", "King Fahd Road",        "Riyadh",       "Saudi Arabia", "MIDDLE_EAST",  24.713600,   46.675300, 2015),
    # ASIA_PACIFIC
    (21, "SIN", "Raffles Place",         "Singapore",    "Singapore",    "ASIA_PACIFIC",  1.283700,  103.851500, 1996),
    (22, "HKG", "Central District",      "Hong Kong",    "Hong Kong",    "ASIA_PACIFIC", 22.279300,  114.162800, 1999),
    (23, "TYO", "Marunouchi",            "Tokyo",        "Japan",        "ASIA_PACIFIC", 35.681200,  139.767100, 1998),
    (24, "SYD", "Martin Place",          "Sydney",       "Australia",    "ASIA_PACIFIC",-33.868800,  151.209300, 2003),
    (25, "MUM", "Bandra Kurla",          "Mumbai",       "India",        "ASIA_PACIFIC", 19.076000,   72.877700, 2008),
    # AMERICAS (augmented)
    (26, "BOS", "Congress Street",       "Boston",       "USA",          "AMERICAS",     42.355400,  -71.060500, 2000),
    (27, "ATL", "Peachtree Street",      "Atlanta",      "USA",          "AMERICAS",     33.749000,  -84.388000, 2009),
    (28, "DEN", "17th Street",           "Denver",       "USA",          "AMERICAS",     39.742500, -104.994000, 2014),
    (29, "YVR", "Georgia Street",        "Vancouver",    "Canada",       "AMERICAS",     49.282700, -123.120700, 2006),
    (30, "LIM", "Av. Javier Prado",      "Lima",         "Peru",         "AMERICAS",    -12.046400,  -77.042800, 2016),
    (31, "BOG", "Carrera Septima",       "Bogota",       "Colombia",     "AMERICAS",      4.711000,  -74.072100, 2017),
    (32, "SCL", "Av. Apoquindo",         "Santiago",     "Chile",        "AMERICAS",    -33.448900,  -70.669300, 2013),
    (33, "BUE", "Av. Corrientes",        "Buenos Aires", "Argentina",    "AMERICAS",    -34.603700,  -58.381600, 2012),
    (34, "PTY", "Calle 50",              "Panama City",  "Panama",       "AMERICAS",      8.982400,  -79.519900, 2018),
    # EUROPE (augmented)
    (35, "FRA", "Neue Mainzer Strasse",  "Frankfurt",    "Germany",      "EUROPE",       50.110900,    8.682100, 1996),
    (36, "MUC", "Maximilianstrasse",     "Munich",       "Germany",      "EUROPE",       48.135100,   11.582000, 2011),
    (37, "LUX", "Avenue de la Liberte",  "Luxembourg",   "Luxembourg",   "EUROPE",       49.611700,    6.130000, 1999),
    (38, "LIS", "Avenida da Liberdade",  "Lisbon",       "Portugal",     "EUROPE",       38.722300,   -9.139300, 2007),
    (39, "STO", "Biblioteksgatan",       "Stockholm",    "Sweden",       "EUROPE",       59.329300,   18.068600, 2001),
    (40, "OSL", "Karl Johans gate",      "Oslo",         "Norway",       "EUROPE",       59.913900,   10.752200, 2008),
    (41, "WAW", "Nowy Swiat",            "Warsaw",       "Poland",       "EUROPE",       52.229700,   21.012200, 2015),
    (42, "PRG", "Wenceslas Square",      "Prague",       "Czechia",      "EUROPE",       50.075500,   14.437800, 2016),
    (43, "ATH", "Syntagma Square",       "Athens",       "Greece",       "EUROPE",       37.983800,   23.727500, 2013),
    # MIDDLE_EAST (augmented)
    (44, "DOH", "Al Corniche",           "Doha",         "Qatar",        "MIDDLE_EAST",  25.285400,   51.531000, 2010),
    (45, "KWI", "Gulf Road",             "Kuwait City",  "Kuwait",       "MIDDLE_EAST",  29.375900,   47.977400, 2012),
    (46, "BAH", "Government Avenue",     "Manama",       "Bahrain",      "MIDDLE_EAST",  26.228500,   50.586000, 2014),
    (47, "AMM", "Zahran Street",         "Amman",        "Jordan",       "MIDDLE_EAST",  31.953900,   35.910600, 2016),
    (48, "IST", "Istiklal Caddesi",      "Istanbul",     "Turkey",       "MIDDLE_EAST",  41.008200,   28.978400, 2011),
    # ASIA_PACIFIC (augmented)
    (49, "SEL", "Teheran-ro",            "Seoul",        "South Korea",  "ASIA_PACIFIC", 37.566500,  126.978000, 2005),
    (50, "SHA", "Nanjing Road",          "Shanghai",     "China",        "ASIA_PACIFIC", 31.230400,  121.473700, 2002),
    (51, "BJS", "Jianguomenwai",         "Beijing",      "China",        "ASIA_PACIFIC", 39.904200,  116.407400, 2004),
    (52, "SZX", "Shennan Boulevard",     "Shenzhen",     "China",        "ASIA_PACIFIC", 22.543100,  114.057900, 2010),
    (53, "BKK", "Sukhumvit Road",        "Bangkok",      "Thailand",     "ASIA_PACIFIC", 13.756300,  100.501800, 2007),
    (54, "KUL", "Jalan Ampang",          "Kuala Lumpur", "Malaysia",     "ASIA_PACIFIC",  3.139000,  101.686900, 2009),
    (55, "CGK", "Jalan Thamrin",         "Jakarta",      "Indonesia",    "ASIA_PACIFIC", -6.208800,  106.845600, 2013),
    (56, "MNL", "Ayala Avenue",          "Manila",       "Philippines",  "ASIA_PACIFIC", 14.599500,  120.984200, 2012),
    (57, "SGN", "Dong Khoi Street",      "Ho Chi Minh City", "Vietnam",  "ASIA_PACIFIC", 10.823100,  106.629700, 2017),
    (58, "TPE", "Xinyi Road",            "Taipei",       "Taiwan",       "ASIA_PACIFIC", 25.033000,  121.565400, 2008),
    (59, "AKL", "Queen Street",          "Auckland",     "New Zealand",  "ASIA_PACIFIC",-36.848500,  174.763300, 2015),
    (60, "MEL", "Collins Street",        "Melbourne",    "Australia",    "ASIA_PACIFIC",-37.813600,  144.963100, 2006),
]

BRANCHES_BY_ID = {b[0]: b for b in BRANCHES}


# (merchant_id, name, mcc_code, category, country, region, latitude, longitude)
MERCHANTS = [
    # AMERICAS
    (1,   "Whole Harvest Market",      "5411", "Groceries",        "USA",    "AMERICAS",     40.758000,  -73.985500),
    (2,   "Metro Rail Coffee",         "5812", "Cafes",            "USA",    "AMERICAS",     40.712800,  -74.006000),
    (3,   "Grand Plaza Hotel",         "7011", "Lodging",          "USA",    "AMERICAS",     40.759000,  -73.984500),
    (4,   "Delta Skies Airlines",      "4511", "Airlines",         "USA",    "AMERICAS",     33.941600,  -118.408500),
    (5,   "Beacon Electronics",        "5732", "Electronics",      "USA",    "AMERICAS",     34.052200,  -118.243700),
    (6,   "Shellstar Fuels",           "5541", "Fuel",             "USA",    "AMERICAS",     33.942500,  -118.255000),
    (7,   "Blue Orchid Dining",        "5812", "Restaurants",      "USA",    "AMERICAS",     25.761700,  -80.191800),
    (8,   "Summit View Casino",        "7995", "Casino",           "USA",    "AMERICAS",     36.114700,  -115.172800),
    (9,   "BitVault Exchange",         "6051", "Crypto exchange",  "USA",    "AMERICAS",     37.774900,  -122.419400),
    (10,  "Global Remit Now",          "4829", "Wire transfer",    "USA",    "AMERICAS",     40.712800,  -74.006000),
    (11,  "Amazonica Retail",          "5999", "General retail",   "USA",    "AMERICAS",     47.606200,  -122.332100),
    (12,  "Luxe Watches NY",           "5094", "Jewelry",          "USA",    "AMERICAS",     40.758000,  -73.985500),
    (13,  "Banco Sol ATM Network",     "6011", "ATM",              "Mexico", "AMERICAS",     19.432600,  -99.133200),
    (14,  "Fiesta Foods",              "5411", "Groceries",        "Brazil", "AMERICAS",    -23.561400,  -46.655900),
    # EUROPE
    (15,  "Harrods Knightsbridge",     "5311", "Department store", "UK",     "EUROPE",       51.499400,   -0.163700),
    (16,  "Monoprix Paris",            "5411", "Groceries",        "France", "EUROPE",       48.870600,    2.335300),
    (17,  "SkyJet Europe",             "4511", "Airlines",         "UK",     "EUROPE",       51.470000,   -0.454300),
    (18,  "Swiss Rail SBB",            "4111", "Transit",          "Switzerland", "EUROPE",  47.376900,    8.541700),
    (19,  "Lombard Street Wine",       "5921", "Liquor",           "UK",     "EUROPE",       51.513300,   -0.088600),
    (20,  "El Corte Ingles Madrid",    "5311", "Department store", "Spain",  "EUROPE",       40.416800,   -3.703800),
    (21,  "Aurum Milano",              "5094", "Jewelry",          "Italy",  "EUROPE",       45.464200,    9.190000),
    (22,  "Berlin Book Nook",          "5942", "Books",            "Germany","EUROPE",       52.520000,   13.405000),
    (23,  "Emerald Isle Golf Club",    "7997", "Recreation",       "Ireland","EUROPE",       53.349800,   -6.260300),
    (24,  "Paris Crypto Desk",         "6051", "Crypto exchange",  "France", "EUROPE",       48.856600,    2.352200),
    # MIDDLE_EAST
    (25,  "Gold Souk Exchange",        "6051", "Gold & forex",     "UAE",    "MIDDLE_EAST",  25.264400,   55.297100),
    (26,  "Desert Pearl Hotel",        "7011", "Lodging",          "UAE",    "MIDDLE_EAST",  25.204800,   55.270800),
    (27,  "CryptoDesk MENA",           "6051", "Crypto exchange",  "UAE",    "MIDDLE_EAST",  25.204800,   55.270800),
    (28,  "Tel Aviv Bistro",           "5812", "Restaurants",      "Israel", "MIDDLE_EAST",  32.085300,   34.781800),
    (29,  "Riyadh Oasis Mall",         "5311", "Department store", "Saudi Arabia", "MIDDLE_EAST", 24.713600, 46.675300),
    (30,  "Sahara Remit House",        "4829", "Wire transfer",    "UAE",    "MIDDLE_EAST",  25.264400,   55.297100),
    # ASIA_PACIFIC
    (31,  "Marina Bay Sands",          "7995", "Casino",           "Singapore", "ASIA_PACIFIC", 1.283700, 103.851500),
    (32,  "Raffles Books",             "5942", "Books",            "Singapore", "ASIA_PACIFIC", 1.290270, 103.851959),
    (33,  "Shinjuku Ginza Dept",       "5311", "Department store", "Japan",  "ASIA_PACIFIC", 35.681200,  139.767100),
    (34,  "Harbour City Mall",         "5311", "Department store", "Hong Kong", "ASIA_PACIFIC", 22.295000, 114.168000),
    (35,  "Sydney Opera Gift",         "5947", "Gifts",            "Australia", "ASIA_PACIFIC", -33.856800, 151.215300),
    (36,  "Lucky Dragon Casino",       "7995", "Casino",           "Macau", "ASIA_PACIFIC", 22.198700,  113.543900),
    (37,  "CryptoMoon Exchange",       "6051", "Crypto exchange",  "Singapore", "ASIA_PACIFIC", 1.352100, 103.819800),
    (38,  "Mumbai Spice Bazaar",       "5812", "Restaurants",      "India",  "ASIA_PACIFIC", 19.076000,   72.877700),
    (39,  "Bondi Surf Shop",           "5651", "Apparel",          "Australia", "ASIA_PACIFIC", -33.890800, 151.274300),
    (40,  "Silk Road Traders HK",      "6051", "Gold & forex",     "Hong Kong", "ASIA_PACIFIC", 22.319300, 114.169400),
    # ---- AMERICAS (augmented) ----
    (41,  "Northstar Remit",           "4829", "Wire transfer",    "USA",    "AMERICAS",     40.712800,  -74.006000),
    (42,  "Silverline Bullion",        "5094", "Precious metals",  "USA",    "AMERICAS",     40.758000,  -73.985500),
    (43,  "Vegas High Roller Club",    "7995", "Casino",           "USA",    "AMERICAS",     36.114700, -115.172800),
    (44,  "Pacific Import Partners",   "5999", "Import/export",    "USA",    "AMERICAS",     33.739500, -118.277500),
    (45,  "Manhattan Art House",       "5971", "Art dealer",       "USA",    "AMERICAS",     40.761400,  -73.977600),
    (46,  "QuickCash Pawn",            "5932", "Pawn broker",      "USA",    "AMERICAS",     32.776700,  -96.797000),
    (47,  "SoCal Motors Luxury",       "5511", "Luxury autos",     "USA",    "AMERICAS",     34.019500, -118.491200),
    (48,  "Everglade Pharmacy",        "5912", "Pharmacy",         "USA",    "AMERICAS",     25.761700,  -80.191800),
    (49,  "Cascade Cloud Hosting",     "7372", "Software",         "USA",    "AMERICAS",     47.606200, -122.332100),
    (50,  "Rocky Mountain Freight",    "4214", "Freight",          "USA",    "AMERICAS",     39.739200, -104.990300),
    (51,  "Maple Leaf Trading",        "5999", "General retail",   "Canada", "AMERICAS",     43.653200,  -79.383200),
    (52,  "Toronto Bullion Depository","5094", "Precious metals",  "Canada", "AMERICAS",     43.648700,  -79.381700),
    (53,  "Cozumel Resorts",           "7011", "Lodging",          "Mexico", "AMERICAS",     20.508300,  -86.945800),
    (54,  "Azteca Money Transfer",     "4829", "Wire transfer",    "Mexico", "AMERICAS",     19.432600,  -99.133200),
    (55,  "Rio Gold Exchange",         "6051", "Gold & forex",     "Brazil", "AMERICAS",    -22.906800,  -43.172900),
    (56,  "Sao Paulo Auto Group",      "5511", "Luxury autos",     "Brazil", "AMERICAS",    -23.561400,  -46.655900),
    (57,  "Andes Coffee Export",       "5999", "Import/export",    "Colombia", "AMERICAS",    4.711000,  -74.072100),
    (58,  "Panama Free Zone Traders",  "5999", "Import/export",    "Panama", "AMERICAS",      8.982400,  -79.519900),
    (59,  "Buenos Aires Exchange House","6051","Gold & forex",     "Argentina", "AMERICAS", -34.603700,  -58.381600),
    (60,  "Lima Textiles Export",      "5999", "Import/export",    "Peru",   "AMERICAS",    -12.046400,  -77.042800),
    (61,  "Santiago Wine Cellars",     "5921", "Liquor",           "Chile",  "AMERICAS",    -33.448900,  -70.669300),
    (62,  "Miami Yacht Brokerage",     "5551", "Boat dealer",      "USA",    "AMERICAS",     25.761700,  -80.191800),
    (63,  "Chicago Futures Desk",      "6211", "Securities",       "USA",    "AMERICAS",     41.878100,  -87.629800),
    (64,  "Atlanta Payroll Services",  "7361", "Payroll",          "USA",    "AMERICAS",     33.749000,  -84.388000),
    (65,  "Denver Crypto Vault",       "6051", "Crypto exchange",  "USA",    "AMERICAS",     39.742500, -104.994000),
    # ---- EUROPE (augmented) ----
    (66,  "Zurich Private Vaults",     "5094", "Precious metals",  "Switzerland", "EUROPE",  47.376900,    8.541700),
    (67,  "Alpine Trust Services",     "6282", "Advisory",         "Liechtenstein", "EUROPE", 47.141000,    9.520900),
    (68,  "Amsterdam Diamond Guild",   "5094", "Jewelry",          "Netherlands", "EUROPE",  52.367600,    4.904100),
    (69,  "Rotterdam Container Lines","4214", "Freight",          "Netherlands", "EUROPE",  51.924400,    4.477700),
    (70,  "Hamburg Trade Finance",     "6082", "Trade finance",    "Germany", "EUROPE",     53.551100,    9.993700),
    (71,  "Berlin Crypto Desk",        "6051", "Crypto exchange",  "Germany", "EUROPE",     52.520000,   13.405000),
    (72,  "Paris Luxury Autos",        "5511", "Luxury autos",     "France", "EUROPE",      48.856600,    2.352200),
    (73,  "Cote d'Azur Resorts",       "7011", "Lodging",          "France", "EUROPE",      43.552800,    7.017400),
    (74,  "Milan Fashion Export",      "5651", "Apparel",          "Italy",  "EUROPE",      45.464200,    9.190000),
    (75,  "Rome Art & Antiquities",    "5971", "Art dealer",       "Italy",  "EUROPE",      41.902800,   12.496400),
    (76,  "Madrid Money Transfer",     "4829", "Wire transfer",    "Spain",  "EUROPE",      40.416800,   -3.703800),
    (77,  "Barcelona Gaming Lounge",   "7994", "Online gaming",    "Spain",  "EUROPE",      41.387400,    2.168600),
    (78,  "Lisbon Golden Visa Advisors","6282","Advisory",         "Portugal", "EUROPE",    38.722300,   -9.139300),
    (79,  "Dublin Fund Administration","6282", "Advisory",         "Ireland", "EUROPE",     53.349800,   -6.260300),
    (80,  "London Bullion Market",     "5094", "Precious metals",  "UK",     "EUROPE",      51.513300,   -0.088600),
    (81,  "Mayfair Private Office",    "6282", "Advisory",         "UK",     "EUROPE",      51.507400,   -0.148300),
    (82,  "Manchester Cash Logistics", "4214", "Freight",          "UK",     "EUROPE",      53.480800,   -2.242600),
    (83,  "Stockholm Fintech Hub",     "7372", "Software",         "Sweden", "EUROPE",      59.329300,   18.068600),
    (84,  "Oslo Offshore Services",    "6282", "Advisory",         "Norway", "EUROPE",      59.913900,   10.752200),
    (85,  "Warsaw Currency Exchange",  "6051", "Gold & forex",     "Poland", "EUROPE",      52.229700,   21.012200),
    (86,  "Prague Gaming House",       "7995", "Casino",           "Czechia","EUROPE",      50.075500,   14.437800),
    (87,  "Athens Shipping Group",     "4411", "Shipping",         "Greece", "EUROPE",      37.983800,   23.727500),
    (88,  "Vienna Private Bank Desk",  "6211", "Securities",       "Austria","EUROPE",      48.208200,   16.373800),
    (89,  "Copenhagen Design Export",  "5999", "Import/export",    "Denmark","EUROPE",      55.676100,   12.568300),
    (90,  "Helsinki Metals Trading",   "5094", "Precious metals",  "Finland","EUROPE",      60.169900,   24.938400),
    # ---- MIDDLE_EAST (augmented) ----
    (91,  "Abu Dhabi Sovereign Desk",  "6211", "Securities",       "UAE",    "MIDDLE_EAST", 24.453900,   54.377300),
    (92,  "Sharjah Gold Refinery",     "5094", "Precious metals",  "UAE",    "MIDDLE_EAST", 25.346300,   55.420900),
    (93,  "Dubai Crypto OTC",          "6051", "Crypto exchange",  "UAE",    "MIDDLE_EAST", 25.204800,   55.270800),
    (94,  "Jebel Ali Re-Export",       "5999", "Import/export",    "UAE",    "MIDDLE_EAST", 24.985700,   55.027200),
    (95,  "Doha Real Estate Holdings", "6531", "Real estate",      "Qatar",  "MIDDLE_EAST", 25.285400,   51.531000),
    (96,  "Kuwait Remittance House",   "4829", "Wire transfer",    "Kuwait", "MIDDLE_EAST", 29.375900,   47.977400),
    (97,  "Manama Exchange Center",    "6051", "Gold & forex",     "Bahrain","MIDDLE_EAST", 26.228500,   50.586000),
    (98,  "Amman Pharma Trading",      "5912", "Pharmacy",         "Jordan", "MIDDLE_EAST", 31.953900,   35.910600),
    (99,  "Istanbul Bazaar Traders",   "5999", "Import/export",    "Turkey", "MIDDLE_EAST", 41.008200,   28.978400),
    (100, "Tel Aviv Cyber Exports",    "7372", "Software",         "Israel", "MIDDLE_EAST", 32.085300,   34.781800),
    (101, "Riyadh Construction Group", "1771", "Construction",     "Saudi Arabia", "MIDDLE_EAST", 24.713600, 46.675300),
    (102, "Jeddah Shipping Lines",     "4411", "Shipping",         "Saudi Arabia", "MIDDLE_EAST", 21.485800, 39.192500),
    (103, "Beirut Trade House",        "5999", "Import/export",    "Lebanon","MIDDLE_EAST", 33.893800,   35.501800),
    (104, "Doha Duty Free Retail",     "5311", "Department store", "Qatar",  "MIDDLE_EAST", 25.260000,   51.564000),
    (105, "Muscat Metals FZE",         "5094", "Precious metals",  "Oman",   "MIDDLE_EAST", 23.588000,   58.382900),
    # ---- ASIA_PACIFIC (augmented) ----
    (106, "Singapore Commodity Desk",  "6211", "Securities",       "Singapore", "ASIA_PACIFIC",  1.283700, 103.851500),
    (107, "Marina Bay Junket Services","7995", "Casino",           "Singapore", "ASIA_PACIFIC",  1.283700, 103.851500),
    (108, "Hong Kong Bullion Ltd",     "5094", "Precious metals",  "Hong Kong", "ASIA_PACIFIC", 22.279300, 114.162800),
    (109, "Kowloon Watch Traders",     "5094", "Jewelry",          "Hong Kong", "ASIA_PACIFIC", 22.319300, 114.169400),
    (110, "Macau VIP Gaming",          "7995", "Casino",           "Macau",  "ASIA_PACIFIC", 22.198700,  113.543900),
    (111, "Shenzhen Electronics Export","5732","Electronics",      "China",  "ASIA_PACIFIC", 22.543100,  114.057900),
    (112, "Shanghai Free Trade Agents","5999", "Import/export",    "China",  "ASIA_PACIFIC", 31.230400,  121.473700),
    (113, "Beijing Pharma Supply",     "5912", "Pharmacy",         "China",  "ASIA_PACIFIC", 39.904200,  116.407400),
    (114, "Tokyo Crypto Exchange",     "6051", "Crypto exchange",  "Japan",  "ASIA_PACIFIC", 35.681200,  139.767100),
    (115, "Osaka Metals Trading",      "5094", "Precious metals",  "Japan",  "ASIA_PACIFIC", 34.693700,  135.502300),
    (116, "Seoul Gaming Studios",      "7994", "Online gaming",    "South Korea", "ASIA_PACIFIC", 37.566500, 126.978000),
    (117, "Busan Shipping Agency",     "4411", "Shipping",         "South Korea", "ASIA_PACIFIC", 35.179600, 129.075600),
    (118, "Taipei Semiconductor Trading","5732","Electronics",     "Taiwan", "ASIA_PACIFIC", 25.033000,  121.565400),
    (119, "Bangkok Gems & Jewelry",    "5094", "Jewelry",          "Thailand","ASIA_PACIFIC", 13.756300,  100.501800),
    (120, "Phuket Resorts Group",      "7011", "Lodging",          "Thailand","ASIA_PACIFIC",  7.880400,   98.392300),
    (121, "KL Palm Oil Export",        "5999", "Import/export",    "Malaysia","ASIA_PACIFIC",  3.139000,  101.686900),
    (122, "Jakarta Mining Services",   "1771", "Construction",     "Indonesia","ASIA_PACIFIC", -6.208800, 106.845600),
    (123, "Manila Remittance Center",  "4829", "Wire transfer",    "Philippines","ASIA_PACIFIC", 14.599500, 120.984200),
    (124, "Ho Chi Minh Garment Export","5651", "Apparel",          "Vietnam","ASIA_PACIFIC", 10.823100,  106.629700),
    (125, "Hanoi Trading Company",     "5999", "Import/export",    "Vietnam","ASIA_PACIFIC", 21.027800,  105.834200),
    (126, "Mumbai Gold Loans",         "5932", "Pawn broker",      "India",  "ASIA_PACIFIC", 19.076000,   72.877700),
    (127, "Delhi Money Changers",      "6051", "Gold & forex",     "India",  "ASIA_PACIFIC", 28.613900,   77.209000),
    (128, "Bangalore IT Exports",      "7372", "Software",         "India",  "ASIA_PACIFIC", 12.971600,   77.594600),
    (129, "Sydney Bullion Vault",      "5094", "Precious metals",  "Australia","ASIA_PACIFIC",-33.868800, 151.209300),
    (130, "Melbourne Gaming Lounge",   "7995", "Casino",           "Australia","ASIA_PACIFIC",-37.813600, 144.963100),
    (131, "Auckland Dairy Export",     "5999", "Import/export",    "New Zealand","ASIA_PACIFIC",-36.848500, 174.763300),
    (132, "Jakarta Digital Wallet",    "6099", "Digital wallet",   "Indonesia","ASIA_PACIFIC", -6.175100, 106.865000),
    (133, "Manila Pawn & Gold",        "5932", "Pawn broker",      "Philippines","ASIA_PACIFIC", 14.609100, 121.022300),
    (134, "Singapore Trade Finance",   "6082", "Trade finance",    "Singapore","ASIA_PACIFIC",  1.290000, 103.850000),
    (135, "Hong Kong Shell Advisory",  "6282", "Advisory",         "Hong Kong","ASIA_PACIFIC", 22.281000, 114.158000),
    (136, "Macau Junket Operators",    "7995", "Casino",           "Macau",  "ASIA_PACIFIC", 22.200000,  113.550000),
    (137, "Tokyo Luxury Autos",        "5511", "Luxury autos",     "Japan",  "ASIA_PACIFIC", 35.658600,  139.745400),
    (138, "Seoul Cosmetics Export",    "5999", "Import/export",    "South Korea","ASIA_PACIFIC", 37.497900, 127.027600),
    (139, "Bangkok Crypto OTC",        "6051", "Crypto exchange",  "Thailand","ASIA_PACIFIC", 13.730800,  100.523000),
    (140, "Mumbai Bullion House",      "5094", "Precious metals",  "India",  "ASIA_PACIFIC", 19.017600,   72.856200),
]

MERCHANTS_BY_ID = {m[0]: m for m in MERCHANTS}

# High-risk corridors used by the AML patterns (merchant ids whose region /
# category the rules treat as elevated risk).
HIGH_RISK_MERCHANT_IDS = [8, 9, 10, 25, 27, 30, 31, 36, 37, 40]

# The augmented world adds merchants in the same elevated-risk categories
# (crypto, gold/forex, money transfer, casino/junket, pawn, art, shell advisory,
# import/export corridors). The canonical list above stays frozen because the
# canonical HIGH_RISK_COUNTRY pattern draws from it.
HIGH_RISK_MERCHANT_IDS_EXT = HIGH_RISK_MERCHANT_IDS + [
    42, 43, 46, 54, 55, 59, 65, 66, 71, 76, 77, 80, 86, 91, 92, 93, 94, 96,
    97, 103, 105, 107, 108, 110, 111, 112, 114, 118, 119, 123, 125, 126, 127,
    129, 133, 135, 136, 139, 140,
]

FIRST_NAMES = [
    "Emma", "Liam", "Olivia", "Noah", "Ava", "Ethan", "Sophia", "Mason",
    "Isabella", "Lucas", "Mia", "James", "Amelia", "Benjamin", "Harper",
    "Elena", "Mateo", "Sofia", "Yusuf", "Fatima", "Chen", "Mei", "Ravi",
    "Ananya", "Diego", "Camila", "Hannah", "Jacob", "Priya", "Arjun",
    "Naomi", "Ezra", "Layla", "Omar", "Zainab", "Kenji", "Yuki", "Wei",
    "Chloe", "Daniel", "Grace", "Samuel", "Nora", "Leo", "Aria", "Hugo",
    "Ingrid", "Lars", "Marta", "Piotr",
]
LAST_NAMES = [
    "Johnson", "Smith", "Garcia", "Brown", "Williams", "Jones", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
    "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King",
    "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green",
    "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Reyes", "Khan", "Al-Farsi", "Tanaka", "Sato", "Sharma",
    "Patel", "Costa", "Silva", "Novak", "Kowalski", "Mueller",
]

SEGMENTS = ["RETAIL"] * 55 + ["PREMIUM"] * 20 + ["SME"] * 15 + ["CORP"] * 10

CUSTOMER_COUNTRIES = [
    "USA", "Canada", "Mexico", "Brazil", "UK", "France", "Germany", "Spain",
    "Italy", "Ireland", "Switzerland", "Netherlands", "UAE", "Israel",
    "Saudi Arabia", "Singapore", "Hong Kong", "Japan", "Australia", "India",
]

ACCOUNT_TYPES = ["CHECKING"] * 50 + ["SAVINGS"] * 30 + ["MONEY_MARKET"] * 10 + ["CREDIT_LINE"] * 10
CURRENCIES = ["USD"] * 70 + ["EUR"] * 12 + ["GBP"] * 8 + ["SGD"] * 5 + ["JPY"] * 5
CARD_TYPES = ["DEBIT"] * 60 + ["CREDIT"] * 35 + ["PREPAID"] * 5

CHANNEL_MIX = ["POS"] * 45 + ["ONLINE"] * 25 + ["ATM"] * 10 + ["WIRE"] * 5 + ["MOBILE"] * 10 + ["BRANCH"] * 5
LOAN_TYPES = ["MORTGAGE", "AUTO", "PERSONAL", "BUSINESS"]

# ---------- Reference data for the AML operational tables --------------------
# Login locations: every branch city plus a handful of pure "travel" cities
# (the ones impossible-travel investigations care about).
LOGIN_CITIES = [(b[3], b[4], b[5], b[6], b[7]) for b in BRANCHES] + [
    ("Las Vegas", "USA", "AMERICAS", 36.169900, -115.140000),
    ("Cancun", "Mexico", "AMERICAS", 21.161900, -86.851500),
    ("Monaco", "Monaco", "EUROPE", 43.738400, 7.424600),
    ("Ibiza", "Spain", "EUROPE", 38.906700, 1.420600),
    ("Bali", "Indonesia", "ASIA_PACIFIC", -8.409500, 115.188900),
    ("Phuket", "Thailand", "ASIA_PACIFIC", 7.880400, 98.392300),
]

OFFICERS = ["A. Duarte", "M. Okafor", "R. Lindqvist", "S. Bhatia",
            "T. Nakamura", "L. Moreau", "D. Whitfield", "K. Haddad"]
WATCHLISTS = ["OFAC_SDN", "EU_CONSOLIDATED", "UN_CONSOLIDATED", "PEP_REGISTER", "ADVERSE_MEDIA"]
DOC_TYPES = ["PASSPORT", "PROOF_OF_ADDRESS", "SOURCE_OF_FUNDS", "UBO_DECLARATION",
             "TAX_ID", "COMPANY_REGISTRY"]
DOC_STATUS = ["VERIFIED"] * 70 + ["PENDING"] * 15 + ["EXPIRED"] * 12 + ["REJECTED"] * 3
PURPOSE_CODES = ["TRAD", "SALA", "GDDS", "INTC", "CASH", "DIVI", "LOAN", "SUPP"]
NOTE_CLASSES = ["ANALYST_NOTE", "ESCALATION", "CUSTOMER_REPLY", "REGULATORY_QUERY", "DISPOSITION"]
HOLDING_COMPANIES = ["Halcyon Holdings Ltd", "Meridian Nominees SA", "Silverline Capital BV",
                     "Blue Harbour Investments", "Cedar Ridge Partners LP",
                     "Atlas Nominee Services", "Pinewood Trust", "Kestrel Global Ltd",
                     "Northgate Holdings Inc", "Sable Rock Investments"]
LOGIN_CHANNELS = ["WEB", "MOBILE", "API", "BRANCH_TERMINAL"]
LOGIN_OUTCOMES = ["SUCCESS"] * 82 + ["FAILED_CHALLENGE"] * 10 + ["BLOCKED"] * 5 + ["MFA_TIMEOUT"] * 3
# USD per 1 unit of currency (the augmented world's daily rate sheet).
FX_BASE = {"EUR": 1.0850, "GBP": 1.2720, "SGD": 0.7420, "JPY": 0.006450,
           "CAD": 0.7320, "AUD": 0.6580, "CHF": 1.1280}
BIC_PREFIX_BY_REGION = {"AMERICAS": "MRDNUS", "EUROPE": "MRDNEU",
                        "MIDDLE_EAST": "MRDNME", "ASIA_PACIFIC": "MRDNAS"}


def _drop_existing(conn):
    for v in ["account_dv", "customer_dv"]:
        try:
            with conn.cursor() as cur:
                cur.execute(f"DROP VIEW {v}")
        except oracledb.DatabaseError:
            pass
    for t in ["case_notes", "kyc_documents", "login_events", "wire_messages",
              "beneficial_owners", "sanctions_screenings", "fx_rates",
              "sar_reports", "loans", "transactions", "cards", "merchants",
              "accounts", "customers", "branches"]:
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


# Narratives and note templates for the operational tables.
SAR_NARRATIVES = {
    "STRUCTURING": ("Multiple cash deposits between $8,000 and $9,999 within a "
                    "short window, consistent with structuring to avoid the "
                    "$10,000 CTR threshold."),
    "GEO_VELOCITY": ("Card purchases in geographically distant regions within "
                     "hours of each other, inconsistent with travel patterns."),
    "HIGH_RISK_COUNTRY": ("Wire transfers to merchants in elevated-risk "
                          "corridors shortly after inbound credits."),
    "RAPID_CASH_OUT": ("Large inbound wire followed by rapid ATM withdrawals "
                       "draining the account within 48 hours."),
    "LARGE_CASH_DEPOSIT": ("Single cash deposit exceeding $50,000 without a "
                           "plausible source of funds."),
}
SCREENING_NOTES = {
    "CLEARED": "Reviewed against {list}; date of birth and address do not match. False positive, no further action.",
    "PENDING": "Name and country match {list}; waiting on identity documents before disposition.",
    "ESCALATED": "Strong match against {list} (score {score}); pattern also present in the transaction monitoring queue.",
}
NOTE_TEXT = {
    "ANALYST_NOTE": "Reviewed the {reason} alert for customer {cid}; pattern confirmed on {n} transactions.",
    "ESCALATION": "Escalated customer {cid} to compliance for {reason}; recommending a SAR update.",
    "CUSTOMER_REPLY": "Customer {cid} provided source-of-funds documentation for the {reason} activity; pending verification.",
    "REGULATORY_QUERY": "Regulator asked for the {reason} file on customer {cid}; response due in ten business days.",
    "DISPOSITION": "Disposition for customer {cid}: {reason} confirmed, filing retained, no account closure at this time.",
}

# ---------- Seed generation ---------------------------------------------------
# Two generations live in this file.
#
#   * The "canonical" world (customers 1-200, accounts 1-250, cards 1-286,
#     transactions 1-1199, the 15 original SARs) is drawn from ``random.seed(42)``
#     in exactly the order it always was, because the workshop docs quote its
#     values (customer 7 = Ravi Hill, card transactions 1125/1126, ...).
#   * The "augmented" world is drawn from a second, independent stream
#     (``EXT_SEED``) and only ever appends: 1,800 more customers, 600 more
#     accounts, ~23,000 more transactions, ~100 more SARs, and the AML
#     operational tables (screenings, ownership, wire messages, logins, KYC,
#     case notes, FX).
#
# Both phases call the same helpers, so a generator change moves both worlds;
# only the draw *order* of the canonical phase is frozen.
EXT_SEED = 20260926
EXTRA_CUSTOMERS = 1800            # customer ids 201..2000
EXTRA_ACCOUNTS = 600              # additional (non-primary) accounts
EXTRA_TXN_RANGE = (4, 14)         # activity per augmented account (canonical: 2-7)
EXTRA_LOANS = 840                 # 900 loans in total
EXTRA_PATTERN_IDS = {             # augmented AML pattern instances per typology
    "STRUCTURING": 30, "GEO_VELOCITY": 24, "HIGH_RISK_COUNTRY": 26,
    "RAPID_CASH_OUT": 20, "LARGE_CASH_DEPOSIT": 18,
}


def _add_customers(rng, rows, used_ssn, cids):
    """One customer row per id in ``cids`` (draw order is part of the contract)."""
    for cid in cids:
        first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
        while True:
            ssn = f"{rng.randint(100, 999)}-{rng.randint(10, 99)}-{rng.randint(1000, 9999)}"
            if ssn not in used_ssn:
                used_ssn.add(ssn)
                break
        # Deliberately hotter risk ratings on a few customers get injected by
        # the fraud patterns below; the base draw keeps most customers cool.
        rr = rng.randint(5, 40)
        if cid % 17 == 0:
            rr = rng.randint(55, 75)
        rows.append((cid, f"{first} {last}", ssn,
                     rng.choice(CUSTOMER_COUNTRIES),
                     rng.choice(SEGMENTS), rr))


def _add_accounts(rng, rows, now, primary_ids, extra_rows, extra_lo, extra_hi, first_id,
                  branches=None):
    branches = BRANCHES if branches is None else branches
    """One primary account per customer id, then ``extra_rows`` extra accounts."""
    aid = first_id
    for cid in primary_ids:
        branch = rng.choice(branches)
        acc_type = rng.choice(ACCOUNT_TYPES)
        opened = now - _dt.timedelta(days=rng.randint(60, 3650))
        base_bal = rng.randint(15_000, 900_000)
        if rng.random() < 0.12:
            base_bal = rng.randint(2_000_000, 25_000_000)
        rows.append((aid, cid, branch[0], acc_type, rng.choice(CURRENCIES),
                     base_bal * 100, opened, "ACTIVE"))
        aid += 1
    # NOTE: the primary loop already consumed ``first_id .. first_id + n - 1``,
    # so the extras continue from ``aid`` — starting them at a customer id would
    # collide with a primary account and trip the ACCOUNT_ID primary key.
    for _ in range(extra_rows):
        cid = rng.randint(extra_lo, extra_hi)
        branch = rng.choice(branches)
        acc_type = rng.choice(ACCOUNT_TYPES)
        opened = now - _dt.timedelta(days=rng.randint(60, 3650))
        rows.append((aid, cid, branch[0], acc_type, rng.choice(CURRENCIES),
                     rng.randint(15_000, 900_000) * 100, opened, "ACTIVE"))
        aid += 1


def _add_cards(rng, rows, now, account_ids, first_id):
    card_id = first_id
    for acc_id in account_ids:
        n_cards = rng.choices([0, 1, 2, 3], weights=[15, 60, 20, 5])[0]
        for _ in range(n_cards):
            ctype = rng.choice(CARD_TYPES)
            digits = "".join(str(rng.randint(0, 9)) for _ in range(12))
            pan = ("4532" if ctype == "DEBIT" else "5412" if ctype == "CREDIT" else "6011") + digits
            rows.append((card_id, acc_id, ctype, pan,
                         now - _dt.timedelta(days=rng.randint(30, 900)),
                         "ACTIVE", rng.randint(500, 5000) * 100))
            card_id += 1
    return card_id


def _add_base_activity(rng, add_txn, now, account_ids, per_account, merchants=None):
    merchants = MERCHANTS if merchants is None else merchants
    """Ordinary account activity: 2-7 transactions per account (4-14 augmented)."""
    for acc_id in account_ids:
        for _ in range(rng.randint(*per_account)):
            channel = rng.choice(CHANNEL_MIX)
            when = now - _dt.timedelta(days=rng.uniform(0, 90), hours=rng.uniform(0, 24))
            if channel in ("POS", "ONLINE"):
                m = rng.choice(merchants)
                amount = rng.randint(500, 200_000)
                ttype = "PURCHASE" if rng.random() < 0.8 else "CARD_PAYMENT"
            elif channel == "ATM":
                m = None
                amount = rng.randint(2_000, 100_000)
                ttype = "WITHDRAWAL" if rng.random() < 0.8 else "DEPOSIT"
            elif channel == "WIRE":
                m = None
                amount = rng.randint(100_000, 10_000_000)
                ttype = "WIRE_IN" if rng.random() < 0.5 else "WIRE_OUT"
            elif channel == "MOBILE":
                m = None
                amount = rng.randint(500, 50_000)
                ttype = "TRANSFER"
            else:  # BRANCH
                m = None
                amount = rng.randint(10_000, 5_000_000)
                ttype = "DEPOSIT" if rng.random() < 0.5 else "WITHDRAWAL"
            # m is a full MERCHANTS row; the transactions table stores merchant_id.
            add_txn(acc_id, m[0] if m else None, when, amount, channel, ttype)


def _pattern_structuring(rng, add_txn, now, first_account_of, customer_ids):
    """Cash deposits just under the $10k CTR threshold, in a short window."""
    for cust_id in customer_ids:
        acc = first_account_of[cust_id]
        start = now - _dt.timedelta(days=rng.randint(12, 20))
        for i in range(rng.randint(8, 12)):
            when = start + _dt.timedelta(hours=i * rng.randint(9, 26))
            add_txn(acc, None, when, rng.randint(800_000, 999_900),
                    "BRANCH" if i % 2 == 0 else "ATM", "DEPOSIT",
                    status="FLAGGED", flag_reason="STRUCTURING")


def _pattern_geo_velocity(rng, add_txn, now, first_account_of, account_branch, customer_ids,
                          merchants=None):
    merchants = MERCHANTS if merchants is None else merchants
    """Home-region purchase, then far-region purchases hours later (one blocked)."""
    for cust_id in customer_ids:
        acc = first_account_of[cust_id]
        home_region = BRANCHES_BY_ID[account_branch[acc]][5]
        far_merchants = [m for m in merchants if m[5] != home_region]
        when0 = now - _dt.timedelta(days=rng.randint(3, 10))
        add_txn(acc, next(m for m in merchants if m[5] == home_region)[0],
                when0, rng.randint(2_000, 20_000), "POS", "PURCHASE")
        add_txn(acc, rng.choice(far_merchants)[0],
                when0 + _dt.timedelta(hours=rng.randint(1, 4)),
                rng.randint(5_000, 80_000), "POS", "PURCHASE",
                status="FLAGGED", flag_reason="GEO_VELOCITY")
        add_txn(acc, rng.choice(far_merchants)[0],
                when0 + _dt.timedelta(hours=rng.randint(2, 3)),
                rng.randint(5_000, 80_000), "POS", "PURCHASE",
                status="BLOCKED", flag_reason="GEO_VELOCITY")


def _pattern_high_risk_country(rng, add_txn, now, first_account_of, customer_ids, merchant_pool):
    """Wire-outs to elevated-risk corridors shortly after an inbound credit."""
    for cust_id in customer_ids:
        acc = first_account_of[cust_id]
        when = now - _dt.timedelta(days=rng.randint(2, 12))
        add_txn(acc, None, when, rng.randint(500_000, 5_000_000),
                "WIRE", "WIRE_IN")
        for _ in range(rng.randint(2, 4)):
            m = MERCHANTS_BY_ID[rng.choice(merchant_pool)]
            add_txn(acc, m[0], when + _dt.timedelta(hours=rng.randint(1, 40)),
                    rng.randint(100_000, 2_000_000), "WIRE", "WIRE_OUT",
                    status="FLAGGED", flag_reason="HIGH_RISK_COUNTRY")


def _pattern_rapid_cash_out(rng, add_txn, now, first_account_of, customer_ids):
    """Large inbound wire, then ATM withdrawals draining it within 48 hours."""
    for cust_id in customer_ids:
        acc = first_account_of[cust_id]
        when = now - _dt.timedelta(days=rng.randint(1, 6))
        add_txn(acc, None, when, rng.randint(10_000_000, 40_000_000),
                "WIRE", "WIRE_IN")
        for i in range(rng.randint(5, 7)):
            add_txn(acc, None, when + _dt.timedelta(hours=i * rng.randint(3, 8)),
                    rng.randint(50_000, 100_000), "ATM", "WITHDRAWAL",
                    status="FLAGGED", flag_reason="RAPID_CASH_OUT")


def _pattern_large_cash(rng, add_txn, now, first_account_of, customer_ids):
    """A single cash deposit above $50k without a plausible source of funds."""
    for cust_id in customer_ids:
        acc = first_account_of[cust_id]
        add_txn(acc, None, now - _dt.timedelta(days=rng.randint(1, 9)),
                rng.randint(5_500_000, 12_000_000), "BRANCH", "DEPOSIT",
                status="FLAGGED", flag_reason="LARGE_CASH_DEPOSIT")


def _add_loans(rng, rows, count, first_id, customer_lo, customer_hi, branches=None):
    branches = BRANCHES if branches is None else branches
    for loan_id in range(first_id, first_id + count):
        cust_id = rng.randint(customer_lo, customer_hi)
        branch = rng.choice(branches)
        ltype = rng.choice(LOAN_TYPES)
        if ltype == "MORTGAGE":
            amt, term = rng.randint(20_000_000, 150_000_000), rng.choice([180, 240, 360])
        elif ltype == "AUTO":
            amt, term = rng.randint(1_500_000, 6_000_000), rng.choice([36, 48, 60])
        elif ltype == "PERSONAL":
            amt, term = rng.randint(500_000, 5_000_000), rng.choice([12, 24, 36])
        else:
            amt, term = rng.randint(5_000_000, 50_000_000), rng.choice([24, 36, 60])
        rows.append((loan_id, cust_id, branch[0], ltype, amt,
                     rng.randint(350, 850), term,
                     rng.choice(["ACTIVE", "ACTIVE", "ACTIVE", "PAID_OFF", "DEFAULTED"])))


def _add_sars(rng, rows, now, first_id, sar_customers, reasons=None):
    """One SAR per customer id. ``reasons`` pins the reason code (the augmented
    world files on the typology that actually fired); without it the reason is
    drawn at random, which is what the canonical 15 always did."""
    for i, cust_id in enumerate(sar_customers):
        reason = reasons[i] if reasons else rng.choice(FLAG_REASONS)
        rows.append((first_id + i, cust_id,
                     now - _dt.timedelta(days=rng.randint(1, 30)),
                     reason, SAR_NARRATIVES[reason],
                     rng.choice(["UNDER_REVIEW", "FILED", "OPEN"])))


def _add_screenings(rng, rows, now, customers, name_of, sample_pct=22):
    """Watchlist screenings: a sample of customers is screened against the lists."""
    for c in customers:
        cid = c[0]
        if rng.randint(1, 100) > sample_pct:
            continue
        score = rng.randint(58, 99)
        if score >= 92:
            disposition = "ESCALATED"
        elif score >= 80:
            disposition = rng.choice(["PENDING", "CLEARED", "CLEARED"])
        else:
            disposition = "CLEARED"
        list_type = rng.choice(WATCHLISTS)
        # Two thirds of hits are the customer's own name (a near-match), the
        # rest are unrelated names that tripped a fuzzy match.
        matched = name_of[cid] if rng.random() < 0.66 \
            else f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        rows.append((len(rows) + 1, cid, now - _dt.timedelta(days=rng.randint(1, 180)),
                     list_type, matched, score, disposition, rng.choice(OFFICERS),
                     SCREENING_NOTES[disposition].format(list=list_type, score=score)))


def _add_beneficial_owners(rng, rows, now, customers, name_of):
    """Declared ownership for SME/CORP customers: direct holders plus a layer 2."""
    company_ids = [c[0] for c in customers if c[4] in ("SME", "CORP")]
    for cid in company_ids:
        remaining, holders = 100.0, rng.randint(1, 3)
        top_owner = None
        for i in range(holders):
            pct = round(remaining if i == holders - 1 else rng.uniform(15, 60), 2)
            if pct <= 0:
                break
            remaining = round(remaining - pct, 2)
            linked = rng.random() < 0.45
            owner_cust = rng.randint(1, 2000) if linked else None
            if owner_cust == cid:
                owner_cust, linked = None, False
            owner_name = name_of[owner_cust] if linked else rng.choice(HOLDING_COMPANIES)
            if i == 0:
                top_owner = owner_name
            rows.append((len(rows) + 1, cid, owner_name, owner_cust, pct, 1,
                         rng.choice(CUSTOMER_COUNTRIES),
                         now - _dt.timedelta(days=rng.randint(30, 1200))))
        # The layer examiners chase: who owns the holder.
        if top_owner and rng.random() < 0.35:
            rows.append((len(rows) + 1, cid, rng.choice(HOLDING_COMPANIES), None,
                         round(rng.uniform(51, 100), 2), 2,
                         rng.choice(["Panama", "Cyprus", "Seychelles", "Malta",
                                     "British Virgin Islands", "Luxembourg"]),
                         now - _dt.timedelta(days=rng.randint(30, 900))))


def _add_wire_messages(rng, rows, transactions, name_of, account_customer,
                       customer_region, customer_country, merchant_name,
                       merchant_region, merchant_country):
    """SWIFT-style detail for every WIRE transaction: who sent what to whom.

    ``WIRE_OUT``: the customer orders the payment, the counterparty receives it.
    ``WIRE_IN``: the counterparty orders it, the customer receives it. The
    beneficiary country is a country (the customer's, or the merchant's).
    """
    for t in transactions:
        (txn_id, acc_id, merch_id, when, _amount, _ccy, _ch, ttype,
         _status, _flag, _region) = t
        if ttype not in ("WIRE_IN", "WIRE_OUT"):
            continue
        cid = account_customer.get(acc_id)
        customer = name_of.get(cid, "Unknown Customer")
        customer_country_value = customer_country.get(cid, rng.choice(CUSTOMER_COUNTRIES))
        counterparty = merchant_name.get(merch_id) or rng.choice(HOLDING_COMPANIES)
        cp_region = merchant_region.get(merch_id, rng.choice(REGIONS))
        cp_country = merchant_country.get(merch_id, rng.choice(CUSTOMER_COUNTRIES))
        outbound = ttype == "WIRE_OUT"
        rows.append((len(rows) + 1, txn_id,
                     BIC_PREFIX_BY_REGION[customer_region[acc_id]] + "33",
                     BIC_PREFIX_BY_REGION[cp_region] + "44",
                     customer if outbound else counterparty,
                     counterparty if outbound else customer,
                     cp_country if outbound else customer_country_value,
                     rng.choice(PURPOSE_CODES),
                     rng.choice(["Invoice settlement", "Family support", "Property purchase",
                                 "Consulting fees", "Royalty payment", "Trade settlement"]),
                     when))


def _add_login_events(rng, rows, now, customer_ids, geo_cases):
    """Digital-banking logins, plus the impossible-travel evidence.

    Coordinates are jittered around the city centre so SDO_WITHIN_DISTANCE
    queries have real distances to work with instead of duplicate points.
    """
    def _point(city):
        name, country, region, lat, lon = city
        return (name, country, region,
                round(lat + rng.uniform(-0.05, 0.05), 6),
                round(lon + rng.uniform(-0.05, 0.05), 6))

    for cid in customer_ids:
        for _ in range(rng.randint(1, 6)):
            city, country, region, lat, lon = _point(rng.choice(LOGIN_CITIES))
            rows.append((len(rows) + 1, cid,
                         now - _dt.timedelta(days=rng.uniform(0, 90), hours=rng.uniform(0, 24)),
                         city, country, region, lat, lon,
                         f"{rng.randint(11, 223)}.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}",
                         f"DEV-{rng.randint(100000, 999999)}",
                         rng.choice(LOGIN_CHANNELS), rng.choice(LOGIN_OUTCOMES)))
    # Impossible travel, in the same hours as the flagged card purchases: the
    # joinable evidence behind a GEO_VELOCITY alert.
    for cid, home_region in geo_cases:
        city, country, region, lat, lon = _point(rng.choice(
            [c for c in LOGIN_CITIES if c[2] != home_region]))
        rows.append((len(rows) + 1, cid,
                     now - _dt.timedelta(days=rng.randint(3, 10), hours=rng.randint(1, 6)),
                     city, country, region, lat, lon,
                     f"{rng.randint(11, 223)}.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}",
                     f"DEV-{rng.randint(100000, 999999)}", "WEB",
                     rng.choice(["SUCCESS", "SUCCESS", "FAILED_CHALLENGE"])))


def _add_kyc_documents(rng, rows, now, customer_ids):
    for cid in customer_ids:
        if rng.randint(1, 100) > 75:
            continue
        for _ in range(rng.randint(1, 3)):
            status = rng.choice(DOC_STATUS)
            if status == "EXPIRED":
                expires = now - _dt.timedelta(days=rng.randint(1, 400))
                received = expires - _dt.timedelta(days=rng.choice([365, 730, 1095]))
            elif status == "VERIFIED":
                received = now - _dt.timedelta(days=rng.randint(10, 900))
                expires = max(now + _dt.timedelta(days=rng.randint(30, 1500)),
                              received + _dt.timedelta(days=365))
            else:  # PENDING / REJECTED: received recently, not yet decided
                received = now - _dt.timedelta(days=rng.randint(1, 120))
                expires = received + _dt.timedelta(days=rng.choice([365, 730]))
            rows.append((len(rows) + 1, cid, rng.choice(DOC_TYPES),
                         rng.choice(CUSTOMER_COUNTRIES), received, expires,
                         status, rng.choice(OFFICERS)))


def _add_case_notes(rng, rows, now, sar_reports):
    for sar in sar_reports:
        for _ in range(rng.randint(1, 3)):
            classification = rng.choice(NOTE_CLASSES)
            rows.append((len(rows) + 1, sar[1], sar[0], rng.choice(OFFICERS),
                         sar[2] - _dt.timedelta(days=rng.randint(0, 6)),
                         classification,
                         NOTE_TEXT[classification].format(cid=sar[1], reason=sar[3],
                                                          n=rng.randint(3, 14))))


def _add_fx_rates(rng, rows, now, days=90):
    for ccy in sorted(FX_BASE):
        rate = FX_BASE[ccy]
        for d in range(days, 0, -1):
            rate = max(rate * (1 + rng.uniform(-0.004, 0.004)), 1e-6)
            rows.append(((now - _dt.timedelta(days=d)).date(), ccy, round(rate, 6)))


def _build_seed():
    """Generate the deterministic Meridian Bank world (see the module docstring).

    Returns a dict of row lists keyed by table name.
    """
    now = _dt.datetime.utcnow()

    # ================= canonical world — FROZEN DRAW ORDER =================
    # Every value below is quoted in the workshop docs; keep the sequence of
    # draws intact when editing. New content belongs in the augmented block.
    rng = random
    rng.seed(42)

    # The canonical world is pinned to the original 25 branches / 40 merchants:
    # ``choice`` picks by index, so widening the pools would silently move which
    # branch or merchant every canonical row points at.
    c_branches, c_merchants = BRANCHES[:25], MERCHANTS[:40]

    customers, used_ssn = [], set()
    _add_customers(rng, customers, used_ssn, range(1, 201))

    accounts = []
    _add_accounts(rng, accounts, now, range(1, 201), 50, 1, 200, first_id=1,
                  branches=c_branches)
    account_branch = {a[0]: a[2] for a in accounts}       # account_id -> branch_id
    account_customer = {a[0]: a[1] for a in accounts}     # account_id -> customer_id
    first_account_of = {}                                 # customer_id -> first account_id
    for a in accounts:
        first_account_of.setdefault(a[1], a[0])

    cards = []
    _add_cards(rng, cards, now, [a[0] for a in accounts], first_id=1)

    transactions = []
    txn_id = 1

    def add_txn(account_id, merchant_id, when, amount_cents, channel, txn_type,
                status="COMPLETED", flag_reason=None):
        nonlocal txn_id
        region = BRANCHES_BY_ID[account_branch[account_id]][5]
        transactions.append((txn_id, account_id, merchant_id, when, amount_cents,
                             "USD", channel, txn_type, status, flag_reason, region))
        txn_id += 1

    _add_base_activity(rng, add_txn, now, [a[0] for a in accounts], (2, 7),
                       merchants=c_merchants)

    _pattern_structuring(rng, add_txn, now, first_account_of, [7, 42, 88, 133])
    _pattern_geo_velocity(rng, add_txn, now, first_account_of, account_branch, [19, 55, 91],
                          merchants=c_merchants)
    _pattern_high_risk_country(rng, add_txn, now, first_account_of, [23, 71, 140, 162],
                               HIGH_RISK_MERCHANT_IDS)
    _pattern_rapid_cash_out(rng, add_txn, now, first_account_of, [30, 117])
    _pattern_large_cash(rng, add_txn, now, first_account_of, [44, 158])

    loans = []
    _add_loans(rng, loans, 60, first_id=1, customer_lo=1, customer_hi=200,
               branches=c_branches)

    sar_reports = []
    _add_sars(rng, sar_reports, now, first_id=1, sar_customers=[
        7, 19, 23, 30, 42, 44, 55, 71, 88, 91, 117, 133, 140, 158, 162])

    # ================= augmented world — INDEPENDENT STREAM =================
    # Adding to this block never moves a canonical value: it draws from its own
    # Random instance and only ever appends rows.
    ext = random.Random(EXT_SEED)
    new_customer_ids = list(range(201, 201 + EXTRA_CUSTOMERS))
    _add_customers(ext, customers, used_ssn, new_customer_ids)
    name_of = {c[0]: c[1] for c in customers}

    pre_accounts = len(accounts)
    _add_accounts(ext, accounts, now, new_customer_ids, EXTRA_ACCOUNTS, 201, 2000,
                  first_id=pre_accounts + 1)
    for a in accounts[pre_accounts:]:
        account_branch[a[0]] = a[2]
        account_customer[a[0]] = a[1]
        first_account_of.setdefault(a[1], a[0])

    _add_cards(ext, cards, now, [a[0] for a in accounts[pre_accounts:]],
               first_id=len(cards) + 1)

    _add_base_activity(ext, add_txn, now, [a[0] for a in accounts[pre_accounts:]],
                       EXTRA_TXN_RANGE)

    # Augmented AML pattern instances: one distinct customer group per typology.
    pattern_groups, claimed = {}, set()
    for typology, n in EXTRA_PATTERN_IDS.items():
        group = []
        while len(group) < n:
            cid = ext.randint(201, 201 + EXTRA_CUSTOMERS - 1)
            if cid not in claimed:
                claimed.add(cid)
                group.append(cid)
        pattern_groups[typology] = group

    _pattern_structuring(ext, add_txn, now, first_account_of, pattern_groups["STRUCTURING"])
    _pattern_geo_velocity(ext, add_txn, now, first_account_of, account_branch,
                          pattern_groups["GEO_VELOCITY"])
    _pattern_high_risk_country(ext, add_txn, now, first_account_of,
                               pattern_groups["HIGH_RISK_COUNTRY"],
                               HIGH_RISK_MERCHANT_IDS_EXT)
    _pattern_rapid_cash_out(ext, add_txn, now, first_account_of,
                            pattern_groups["RAPID_CASH_OUT"])
    _pattern_large_cash(ext, add_txn, now, first_account_of,
                        pattern_groups["LARGE_CASH_DEPOSIT"])

    # A desk orders its queue by customer risk: the customers under
    # investigation carry the hot ratings.
    hot_ids = set().union(*pattern_groups.values())
    for i, row in enumerate(customers):
        if row[0] in hot_ids:
            customers[i] = row[:5] + (ext.randint(55, 85),)

    _add_loans(ext, loans, EXTRA_LOANS, first_id=len(loans) + 1,
               customer_lo=201, customer_hi=201 + EXTRA_CUSTOMERS - 1)

    # SARs for the augmented alerts, filed on the typology that actually fired
    # (~85% of alerts become a filing; the rest stay in the analyst queue).
    extra_sar_customers, extra_sar_reasons = [], []
    for typology, group in pattern_groups.items():
        for cid in group:
            if ext.random() < 0.85:
                extra_sar_customers.append(cid)
                extra_sar_reasons.append(typology)
    _add_sars(ext, sar_reports, now, first_id=len(sar_reports) + 1,
              sar_customers=extra_sar_customers, reasons=extra_sar_reasons)

    # ---------- AML operational tables ----------
    sanctions_screenings, beneficial_owners, wire_messages = [], [], []
    login_events, kyc_documents, case_notes, fx_rates = [], [], [], []

    _add_screenings(ext, sanctions_screenings, now, customers, name_of)
    _add_beneficial_owners(ext, beneficial_owners, now, customers, name_of)
    _add_wire_messages(ext, wire_messages, transactions, name_of, account_customer,
                       customer_region={a: BRANCHES_BY_ID[b][5]
                                        for a, b in account_branch.items()},
                       customer_country={c[0]: c[3] for c in customers},
                       merchant_name={m[0]: m[1] for m in MERCHANTS},
                       merchant_region={m[0]: m[5] for m in MERCHANTS},
                       merchant_country={m[0]: m[4] for m in MERCHANTS})
    geo_cases = [(cid, BRANCHES_BY_ID[account_branch[first_account_of[cid]]][5])
                 for cid in pattern_groups["GEO_VELOCITY"]]
    _add_login_events(ext, login_events, now, list(range(1, 201 + EXTRA_CUSTOMERS)),
                      geo_cases)
    _add_kyc_documents(ext, kyc_documents, now, list(range(1, 201 + EXTRA_CUSTOMERS)))
    _add_case_notes(ext, case_notes, now, sar_reports)
    _add_fx_rates(ext, fx_rates, now)

    return {
        "customers": customers,
        "accounts": accounts,
        "cards": cards,
        "transactions": transactions,
        "loans": loans,
        "sar_reports": sar_reports,
        "sanctions_screenings": sanctions_screenings,
        "beneficial_owners": beneficial_owners,
        "wire_messages": wire_messages,
        "login_events": login_events,
        "kyc_documents": kyc_documents,
        "case_notes": case_notes,
        "fx_rates": fx_rates,
    }

def _insert_data(conn, seed_data):
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO branches (branch_id, branch_code, name, city, country, region, "
            "                      latitude, longitude, location, opened_year) "
            "VALUES (:id, :code, :name, :city, :country, :region, :lat, :lon, "
            "        SDO_GEOMETRY(2001, 8307, SDO_POINT_TYPE(:lon, :lat, NULL), NULL, NULL), :year)",
            [
                {"id": b[0], "code": b[1], "name": b[2], "city": b[3],
                 "country": b[4], "region": b[5], "lat": b[6], "lon": b[7], "year": b[8]}
                for b in BRANCHES
            ],
        )
        cur.executemany(
            "INSERT INTO merchants (merchant_id, name, mcc_code, category, country, "
            "                       region, latitude, longitude, location) "
            "VALUES (:id, :name, :mcc, :cat, :country, :region, :lat, :lon, "
            "        SDO_GEOMETRY(2001, 8307, SDO_POINT_TYPE(:lon, :lat, NULL), NULL, NULL))",
            [
                {"id": m[0], "name": m[1], "mcc": m[2], "cat": m[3],
                 "country": m[4], "region": m[5], "lat": m[6], "lon": m[7]}
                for m in MERCHANTS
            ],
        )
        cur.executemany(
            "INSERT INTO customers VALUES (:1, :2, :3, :4, :5, :6)",
            seed_data["customers"],
        )
        cur.executemany(
            "INSERT INTO accounts VALUES (:1, :2, :3, :4, :5, :6, :7, :8)",
            seed_data["accounts"],
        )
        cur.executemany(
            "INSERT INTO cards VALUES (:1, :2, :3, :4, :5, :6, :7)",
            seed_data["cards"],
        )
        cur.executemany(
            "INSERT INTO transactions VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11)",
            seed_data["transactions"],
        )
        cur.executemany(
            "INSERT INTO loans VALUES (:1, :2, :3, :4, :5, :6, :7, :8)",
            seed_data["loans"],
        )
        cur.executemany(
            "INSERT INTO sar_reports VALUES (:1, :2, :3, :4, :5, :6)",
            seed_data["sar_reports"],
        )
        cur.executemany(
            "INSERT INTO sanctions_screenings VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9)",
            seed_data["sanctions_screenings"],
        )
        cur.executemany(
            "INSERT INTO beneficial_owners VALUES (:1, :2, :3, :4, :5, :6, :7, :8)",
            seed_data["beneficial_owners"],
        )
        cur.executemany(
            "INSERT INTO wire_messages VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10)",
            seed_data["wire_messages"],
        )
        cur.executemany(
            "INSERT INTO login_events (event_id, customer_id, event_ts, city, country, "
            "                          region, latitude, longitude, location, ip_address, "
            "                          device_id, channel, outcome) "
            "VALUES (:id, :cid, :ts, :city, :country, :region, :lat, :lon, "
            "        SDO_GEOMETRY(2001, 8307, SDO_POINT_TYPE(:lon, :lat, NULL), NULL, NULL), "
            "        :ip, :device, :channel, :outcome)",
            [
                {"id": r[0], "cid": r[1], "ts": r[2], "city": r[3], "country": r[4],
                 "region": r[5], "lat": r[6], "lon": r[7], "ip": r[8],
                 "device": r[9], "channel": r[10], "outcome": r[11]}
                for r in seed_data["login_events"]
            ],
        )
        cur.executemany(
            "INSERT INTO kyc_documents VALUES (:1, :2, :3, :4, :5, :6, :7, :8)",
            seed_data["kyc_documents"],
        )
        cur.executemany(
            "INSERT INTO case_notes VALUES (:1, :2, :3, :4, :5, :6, :7)",
            seed_data["case_notes"],
        )
        cur.executemany(
            "INSERT INTO fx_rates (rate_date, currency, usd_rate) VALUES (:1, :2, :3)",
            seed_data["fx_rates"],
        )
    conn.commit()


# ---------- Duality views ----------------------------------------------------
DV_DDL = [
    """CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW account_dv AS
       SELECT JSON {
         '_id'          : a.account_id,
         'accountType'  : a.account_type,
         'currency'     : a.currency,
         'balanceCents' : a.balance_cents,
         'status'       : a.status,
         'openedTs'     : a.opened_ts,
         'region'       : (SELECT JSON {
                              'branchCode' : b.branch_code, 'name' : b.name,
                              'city' : b.city, 'country' : b.country,
                              'region' : b.region
                            } FROM branches b WHERE b.branch_id = a.branch_id),
         'customer'     : (SELECT JSON {
                              'customerId' : cu.customer_id, 'fullName' : cu.full_name,
                              'ssn' : cu.ssn, 'segment' : cu.segment,
                              'riskRating' : cu.risk_rating
                            } FROM customers cu WHERE cu.customer_id = a.customer_id),
         'cards'        : [SELECT JSON {
                              'cardId' : ca.card_id, 'cardType' : ca.card_type,
                              'cardNumber' : ca.card_number, 'status' : ca.status,
                              'dailyLimitCents' : ca.daily_limit_cents
                            } FROM cards ca WHERE ca.account_id = a.account_id],
         'transactions' : [SELECT JSON {
                              'txnId' : t.txn_id, 'txnTs' : t.txn_ts,
                              'amountCents' : t.amount_cents, 'currency' : t.currency,
                              'channel' : t.channel, 'txnType' : t.txn_type,
                              'status' : t.status, 'flagReason' : t.flag_reason,
                              'region' : t.region,
                              'merchant' : (SELECT JSON {
                                              'merchantId' : m.merchant_id,
                                              'name' : m.name, 'mccCode' : m.mcc_code,
                                              'category' : m.category,
                                              'country' : m.country
                                            } FROM merchants m WHERE m.merchant_id = t.merchant_id),
                              'wireMessage' : (SELECT JSON {
                                                 'messageId' : w.message_id,
                                                 'senderBic' : w.sender_bic,
                                                 'receiverBic' : w.receiver_bic,
                                                 'beneficiaryName' : w.beneficiary_name,
                                                 'beneficiaryCountry' : w.beneficiary_country,
                                                 'purposeCode' : w.purpose_code
                                               } FROM wire_messages w WHERE w.txn_id = t.txn_id)
                            } FROM transactions t WHERE t.account_id = a.account_id]
       } FROM accounts a""",

    """CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW customer_dv AS
       SELECT JSON {
         '_id'         : cu.customer_id,
         'fullName'    : cu.full_name,
         'ssn'         : cu.ssn,
         'segment'     : cu.segment,
         'riskRating'  : cu.risk_rating,
         'country'     : cu.country,
         'accounts'    : [SELECT JSON {
                            'accountId' : a.account_id, 'accountType' : a.account_type,
                            'currency' : a.currency, 'balanceCents' : a.balance_cents,
                            'status' : a.status,
                            'branch' : (SELECT JSON {
                                          'branchCode' : b.branch_code, 'name' : b.name,
                                          'city' : b.city, 'region' : b.region
                                        } FROM branches b WHERE b.branch_id = a.branch_id)
                          } FROM accounts a WHERE a.customer_id = cu.customer_id],
         'loans'       : [SELECT JSON {
                            'loanId' : l.loan_id, 'loanType' : l.loan_type,
                            'amountCents' : l.amount_cents, 'rateBp' : l.rate_bp,
                            'termMonths' : l.term_months, 'status' : l.status
                          } FROM loans l WHERE l.customer_id = cu.customer_id],
         'sanctionsScreenings' : [SELECT JSON {
                            'screeningId' : s.screening_id, 'listType' : s.list_type,
                            'matchScore' : s.match_score, 'disposition' : s.disposition,
                            'screenedTs' : s.screened_ts
                          } FROM sanctions_screenings s WHERE s.customer_id = cu.customer_id],
         'kycDocuments': [SELECT JSON {
                            'documentId' : d.document_id, 'docType' : d.doc_type,
                            'status' : d.status, 'expiresTs' : d.expires_ts
                          } FROM kyc_documents d WHERE d.customer_id = cu.customer_id],
         'beneficialOwners' : [SELECT JSON {
                            'ownershipId' : o.ownership_id, 'ownerName' : o.owner_name,
                            'ownershipPct' : o.ownership_pct, 'layer' : o.layer,
                            'jurisdiction' : o.jurisdiction
                          } FROM beneficial_owners o WHERE o.company_id = cu.customer_id]
       } FROM customers cu""",
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
    print("Dropping existing bank objects...")
    _drop_existing(conn)

    print("Creating tables...")
    _create_schema(conn)

    print("Wiring spatial metadata + indexes...")
    _create_spatial(conn)

    print("Generating deterministic seed data...")
    data = _build_seed()

    print(f"Inserting: {len(BRANCHES)} branches, {len(MERCHANTS)} merchants, "
          f"{len(data['customers'])} customers, {len(data['accounts'])} accounts, "
          f"{len(data['cards'])} cards, {len(data['transactions'])} transactions, "
          f"{len(data['loans'])} loans, {len(data['sar_reports'])} SAR reports...")
    print(f"           + {len(data['sanctions_screenings'])} sanctions screenings, "
          f"{len(data['beneficial_owners'])} ownership records, "
          f"{len(data['wire_messages'])} wire messages, "
          f"{len(data['login_events'])} login events, "
          f"{len(data['kyc_documents'])} KYC documents, "
          f"{len(data['case_notes'])} case notes, "
          f"{len(data['fx_rates'])} FX rates...")
    _insert_data(conn, data)

    print("Creating JSON Relational Duality Views (account_dv, customer_dv)...")
    _create_duality_views(conn)

    # Statistics matter twice over: the optimizer needs them for plans on
    # 20k+ row tables, and the memory scanner reports ALL_TABLES.NUM_ROWS as
    # the agent's "approximate row count" fact.
    print("Gathering optimizer statistics...")
    with conn.cursor() as cur:
        cur.execute("BEGIN DBMS_STATS.GATHER_SCHEMA_STATS(ownname => USER, cascade => TRUE, "
                    "                   degree => 4); END;")
    conn.commit()

    flagged = sum(1 for t in data["transactions"] if t[8] in ("FLAGGED", "BLOCKED"))
    by_typology = {}
    for t in data["transactions"]:
        if t[9]:
            by_typology[t[9]] = by_typology.get(t[9], 0) + 1
    print(f"\nFINANCE seeded. {flagged} transactions carry an AML flag/block: "
          + ", ".join(f"{k} {v}" for k, v in sorted(by_typology.items())))
