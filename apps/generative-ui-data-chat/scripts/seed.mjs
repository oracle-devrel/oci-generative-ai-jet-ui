import oracledb from "oracledb";

const config = {
  user: process.env.ORACLE_USER || "DATA_CHAT",
  password: process.env.ORACLE_PASSWORD || "DataChatPwd_2026",
  connectionString: process.env.ORACLE_CONNECTION_STRING || "127.0.0.1:1522/FREEPDB1"
};

const revenueRows = [
  ["2025-04-01", 1280000, 1740000, 180000, 42000, "Expansion from retail accounts offset small-business churn."],
  ["2025-05-01", 1345000, 1810000, 205000, 38000, "Enterprise services pipeline continued to build."],
  ["2025-06-01", 1390000, 1885000, 215000, 45000, "Usage-based revenue rose after analytics rollout."],
  ["2025-07-01", 1465000, 1920000, 232000, 41000, "Mid-market adoption accelerated in the west region."],
  ["2025-08-01", 1510000, 1985000, 240000, 46000, "Contract renewals landed ahead of forecast."],
  ["2025-09-01", 1575000, 2060000, 260000, 52000, "Public sector buying cycle contributed to growth."],
  ["2025-10-01", 1640000, 2140000, 278000, 50000, "Premium support attach rate improved."],
  ["2025-11-01", 1695000, 2210000, 290000, 55000, "Expansion from Northeast customers closed early."],
  ["2025-12-01", 1780000, 2300000, 330000, 58000, "Seasonal enterprise true-ups drove the high point."],
  ["2026-01-01", 1715000, 2245000, 245000, 62000, "Normal post-year-end reset with healthy pipeline."],
  ["2026-02-01", 1760000, 2325000, 265000, 60000, "New user growth recovered across core accounts."],
  ["2026-03-01", 1585000, 2290000, 155000, 82000, "March dip tied to delayed onboarding and renewal timing."],
  ["2026-04-01", 1845000, 2410000, 350000, 57000, "Delayed March expansion recognized in April."]
];

const accounts = [
  ["Helio Stores", "West", "Enterprise", "Q1", 820000, 4],
  ["Northstar Bank", "Northeast", "Enterprise", "Q1", 760000, 3],
  ["BluePeak Health", "Central", "Mid-market", "Q1", 645000, 3],
  ["Summit Logistics", "South", "Enterprise", "Q1", 610000, 2],
  ["CivicCloud", "Public Sector", "Enterprise", "Q1", 590000, 2],
  ["Acme Manufacturing", "West", "Mid-market", "Q1", 440000, 2],
  ["Greenline Energy", "South", "Mid-market", "Q1", 390000, 1],
  ["Riverton Media", "Northeast", "SMB", "Q1", 210000, 1]
];

const activeUsers = [
  ["2025-10-01", 41820],
  ["2025-11-01", 43610],
  ["2025-12-01", 45940],
  ["2026-01-01", 44180],
  ["2026-02-01", 46890],
  ["2026-03-01", 45220],
  ["2026-04-01", 49110]
];

const contracts = [
  {
    id: 101,
    account: "Helio Stores",
    title: "Helio Stores Master Cloud Agreement",
    region: "West",
    value: 1280000,
    renewalType: "auto-renewal",
    chunks: [
      [
        "The subscription automatically renews for successive twelve-month terms unless either party gives written notice at least sixty days before the renewal date.",
        "Helio MSA section 8.2",
        "[0.96,0.88,0.12,0.04,0.08,0.03,0.02,0.02]"
      ],
      [
        "A March deployment milestone moved into April after data migration validation required additional customer sign-off.",
        "Helio implementation addendum",
        "[0.12,0.16,0.94,0.86,0.72,0.08,0.05,0.03]"
      ]
    ]
  },
  {
    id: 102,
    account: "Northstar Bank",
    title: "Northstar Bank Analytics Expansion",
    region: "Northeast",
    value: 980000,
    renewalType: "manual renewal",
    chunks: [
      [
        "Renewal requires a signed order form, but committed expansion seats were approved for the April billing cycle after procurement review.",
        "Northstar order form note",
        "[0.24,0.30,0.83,0.78,0.70,0.16,0.08,0.05]"
      ],
      [
        "The customer expanded fraud analytics usage across two divisions, increasing forecast pipeline while delaying recognized revenue until onboarding completion.",
        "Northstar success plan",
        "[0.14,0.17,0.88,0.80,0.68,0.15,0.06,0.04]"
      ]
    ]
  },
  {
    id: 103,
    account: "BluePeak Health",
    title: "BluePeak Health Data Platform Agreement",
    region: "Central",
    value: 740000,
    renewalType: "auto-renewal",
    chunks: [
      [
        "This agreement includes an auto-renewal clause for one-year periods with a price uplift capped at four percent per renewal term.",
        "BluePeak DPA section 11.4",
        "[0.92,0.86,0.16,0.08,0.10,0.04,0.03,0.02]"
      ],
      [
        "Clinical analytics adoption remained above target in March, but invoicing for the add-on module begins only after security review completion.",
        "BluePeak add-on schedule",
        "[0.10,0.14,0.79,0.82,0.71,0.10,0.05,0.04]"
      ]
    ]
  },
  {
    id: 104,
    account: "Summit Logistics",
    title: "Summit Logistics Supply Chain AI Terms",
    region: "South",
    value: 690000,
    renewalType: "auto-renewal",
    chunks: [
      [
        "Unless terminated ninety days before the anniversary date, the supply chain AI subscription renews automatically for the same committed capacity.",
        "Summit terms section 6.1",
        "[0.90,0.84,0.11,0.06,0.09,0.04,0.04,0.02]"
      ]
    ]
  },
  {
    id: 105,
    account: "CivicCloud",
    title: "CivicCloud Public Sector Services Schedule",
    region: "Public Sector",
    value: 640000,
    renewalType: "manual renewal",
    chunks: [
      [
        "Public sector funding approval shifted a planned March services start to April, temporarily lowering recognized revenue while preserving total contract value.",
        "CivicCloud services schedule",
        "[0.08,0.10,0.90,0.85,0.74,0.09,0.05,0.03]"
      ]
    ]
  }
];

async function ignoreDrop(connection, statement) {
  try {
    await connection.execute(statement);
  } catch {
    // Objects may not exist on the first seed run.
  }
}

async function main() {
  const connection = await oracledb.getConnection(config);

  try {
    console.log("Dropping old objects...");
    await ignoreDrop(connection, "DROP INDEX contract_chunks_text_idx");
    await ignoreDrop(connection, "DROP INDEX contract_chunks_vec_idx");
    await ignoreDrop(connection, "DROP TABLE contract_chunks CASCADE CONSTRAINTS PURGE");
    await ignoreDrop(connection, "DROP TABLE contracts CASCADE CONSTRAINTS PURGE");
    await ignoreDrop(connection, "DROP TABLE active_user_metrics CASCADE CONSTRAINTS PURGE");
    await ignoreDrop(connection, "DROP TABLE accounts CASCADE CONSTRAINTS PURGE");
    await ignoreDrop(connection, "DROP TABLE revenue_metrics CASCADE CONSTRAINTS PURGE");

    console.log("Creating tables...");
    await connection.execute(`
      CREATE TABLE revenue_metrics (
        month_start DATE PRIMARY KEY,
        revenue NUMBER(12,2) NOT NULL,
        pipeline NUMBER(12,2) NOT NULL,
        expansion NUMBER(12,2) NOT NULL,
        churn NUMBER(12,2) NOT NULL,
        note VARCHAR2(500)
      )
    `);
    await connection.execute(`
      CREATE TABLE accounts (
        account_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        account_name VARCHAR2(120) NOT NULL,
        region VARCHAR2(80) NOT NULL,
        segment VARCHAR2(80) NOT NULL,
        fiscal_quarter VARCHAR2(8) NOT NULL,
        q1_revenue NUMBER(12,2) NOT NULL,
        active_contracts NUMBER NOT NULL
      )
    `);
    await connection.execute(`
      CREATE TABLE active_user_metrics (
        month_start DATE PRIMARY KEY,
        active_users NUMBER NOT NULL
      )
    `);
    await connection.execute(`
      CREATE TABLE contracts (
        contract_id NUMBER PRIMARY KEY,
        account_name VARCHAR2(120) NOT NULL,
        contract_title VARCHAR2(180) NOT NULL,
        region VARCHAR2(80) NOT NULL,
        contract_value NUMBER(12,2) NOT NULL,
        renewal_type VARCHAR2(80) NOT NULL
      )
    `);
    await connection.execute(`
      CREATE TABLE contract_chunks (
        chunk_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        contract_id NUMBER NOT NULL REFERENCES contracts(contract_id),
        account_name VARCHAR2(120) NOT NULL,
        contract_title VARCHAR2(180) NOT NULL,
        chunk_text CLOB NOT NULL,
        citation_label VARCHAR2(180) NOT NULL,
        embedding VECTOR(8, FLOAT32) NOT NULL
      )
    `);

    console.log("Seeding metrics...");
    await connection.executeMany(
      `INSERT INTO revenue_metrics (month_start, revenue, pipeline, expansion, churn, note)
       VALUES (TO_DATE(:1, 'YYYY-MM-DD'), :2, :3, :4, :5, :6)`,
      revenueRows
    );
    await connection.executeMany(
      `INSERT INTO accounts (account_name, region, segment, fiscal_quarter, q1_revenue, active_contracts)
       VALUES (:1, :2, :3, :4, :5, :6)`,
      accounts
    );
    await connection.executeMany(
      `INSERT INTO active_user_metrics (month_start, active_users)
       VALUES (TO_DATE(:1, 'YYYY-MM-DD'), :2)`,
      activeUsers
    );

    console.log("Seeding contracts and vector chunks...");
    for (const contract of contracts) {
      await connection.execute(
        `INSERT INTO contracts (contract_id, account_name, contract_title, region, contract_value, renewal_type)
         VALUES (:id, :account, :title, :region, :value, :renewalType)`,
        {
          id: contract.id,
          account: contract.account,
          title: contract.title,
          region: contract.region,
          value: contract.value,
          renewalType: contract.renewalType
        }
      );

      for (const [text, citation, embedding] of contract.chunks) {
        await connection.execute(
          `INSERT INTO contract_chunks (contract_id, account_name, contract_title, chunk_text, citation_label, embedding)
           VALUES (:contractId, :account, :title, :text, :citation, TO_VECTOR(:embedding))`,
          {
            contractId: contract.id,
            account: contract.account,
            title: contract.title,
            text,
            citation,
            embedding
          }
        );
      }
    }

    console.log("Creating search indexes...");
    await connection.execute("CREATE INDEX contract_chunks_text_idx ON contract_chunks(chunk_text) INDEXTYPE IS CTXSYS.CONTEXT");
    try {
      await connection.execute(`
        CREATE VECTOR INDEX contract_chunks_vec_idx
        ON contract_chunks (embedding)
        ORGANIZATION INMEMORY NEIGHBOR GRAPH
        DISTANCE COSINE
        WITH TARGET ACCURACY 90
      `);
    } catch (error) {
      console.warn("Vector index creation skipped. Vector search still works, but indexed ANN may require vector memory configuration.");
      console.warn(error.message);
    }

    await connection.commit();

    const verification = await connection.execute(
      `SELECT 'revenue_metrics' AS table_name, COUNT(*) AS row_count FROM revenue_metrics
       UNION ALL SELECT 'accounts', COUNT(*) FROM accounts
       UNION ALL SELECT 'active_user_metrics', COUNT(*) FROM active_user_metrics
       UNION ALL SELECT 'contracts', COUNT(*) FROM contracts
       UNION ALL SELECT 'contract_chunks', COUNT(*) FROM contract_chunks`,
      {},
      { outFormat: oracledb.OUT_FORMAT_OBJECT }
    );

    console.table(verification.rows);
    console.log("Seed complete.");
  } finally {
    await connection.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
