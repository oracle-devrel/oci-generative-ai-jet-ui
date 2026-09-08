import "dotenv/config";
import { readFile, readdir } from "node:fs/promises";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import oracledb from "oracledb";

const MIGRATIONS_DIR = join(
  dirname(fileURLToPath(import.meta.url)),
  "..",
  "packages",
  "db",
  "migrations"
);

const BOOTSTRAP_PREFIX = "000_";
const IDP_PASSWORD_PLACEHOLDER = "<YOUR_IDP_PASSWORD>";

function splitStatements(sql: string): string[] {
  const lines = sql.split("\n");
  const out: string[] = [];
  let current = "";
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed === "/") {
      if (current.trim()) {
        out.push(current.trim());
        current = "";
      }
      continue;
    }
    current += line + "\n";
    if (trimmed.endsWith(";") && !current.toUpperCase().includes("BEGIN")) {
      out.push(current.trim().replace(/;\s*$/, ""));
      current = "";
    }
  }
  if (current.trim()) out.push(current.trim().replace(/;\s*$/, ""));
  return out
    .map((s) =>
      s
        .split("\n")
        .filter((line) => !line.trim().startsWith("--"))
        .join("\n")
        .trim()
    )
    .filter((s) => s.length > 0);
}

interface RunOptions {
  substitutions?: Record<string, string>;
}

async function runFile(
  conn: oracledb.Connection,
  path: string,
  opts: RunOptions = {}
): Promise<void> {
  let sql = await readFile(path, "utf-8");
  for (const [needle, value] of Object.entries(opts.substitutions ?? {})) {
    sql = sql.split(needle).join(value);
  }
  const statements = splitStatements(sql);
  console.log(`\n→ ${path} (${statements.length} statements)`);
  for (const stmt of statements) {
    try {
      await conn.execute(stmt);
      console.log(`  ✓ ${stmt.slice(0, 70).replace(/\s+/g, " ")}…`);
    } catch (err) {
      const code = (err as { errorNum?: number }).errorNum;
      if (code === 955 || code === 1921 || code === 1418 || code === 29879) {
        console.log(`  · already exists (ORA-${code}), continuing`);
        continue;
      }
      throw err;
    }
  }
}

function connectionParams(user: string, password: string): oracledb.ConnectionAttributes {
  const params: oracledb.ConnectionAttributes = {
    user,
    password,
    connectString: process.env.ORACLE_CONNECT_STRING!,
  };
  if (process.env.ORACLE_WALLET_LOCATION) {
    params.walletLocation = process.env.ORACLE_WALLET_LOCATION;
  }
  if (process.env.ORACLE_WALLET_PASSWORD) {
    params.walletPassword = process.env.ORACLE_WALLET_PASSWORD;
  }
  return params;
}

async function main() {
  const skipBootstrap = process.argv.includes("--skip-bootstrap");
  const required = ["ORACLE_CONNECT_STRING", "ORACLE_USER", "ORACLE_PASSWORD"];
  for (const name of required) {
    if (!process.env[name]) throw new Error(`${name} env var is required`);
  }

  const idpUser = process.env.ORACLE_USER!;
  const idpPassword = process.env.ORACLE_PASSWORD!;
  const adminPassword = process.env.ORACLE_ADMIN_PASSWORD;

  const allFiles = (await readdir(MIGRATIONS_DIR)).filter((f) => f.endsWith(".sql")).sort();
  const bootstrapFiles = allFiles.filter((f) => f.startsWith(BOOTSTRAP_PREFIX));
  const schemaFiles = allFiles.filter((f) => !f.startsWith(BOOTSTRAP_PREFIX));

  if (!skipBootstrap && bootstrapFiles.length > 0) {
    if (!adminPassword) {
      throw new Error(
        "ORACLE_ADMIN_PASSWORD env var is required to run bootstrap migrations. " +
          "Set it in .env, or pass --skip-bootstrap if the idp user already exists."
      );
    }
    console.log(`\nPhase 1: ADMIN bootstrap (creating ${idpUser} user)`);
    const adminConn = await oracledb.getConnection(connectionParams("ADMIN", adminPassword));
    adminConn.callTimeout = 60_000;
    try {
      for (const f of bootstrapFiles) {
        await runFile(adminConn, join(MIGRATIONS_DIR, f), {
          substitutions: { [IDP_PASSWORD_PLACEHOLDER]: idpPassword },
        });
      }
      await adminConn.commit();
    } finally {
      await adminConn.close();
    }
  }

  console.log(`\nPhase 2: schema migrations as ${idpUser}`);
  const conn = await oracledb.getConnection(connectionParams(idpUser, idpPassword));
  conn.callTimeout = 60_000;
  try {
    for (const f of schemaFiles) {
      await runFile(conn, join(MIGRATIONS_DIR, f));
    }
    await conn.commit();
    console.log("\nAll migrations applied.");
  } finally {
    await conn.close();
  }
}

main().catch((err) => {
  console.error("db-setup failed:", err);
  process.exit(1);
});
