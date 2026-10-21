import oracledb from "oracledb";

import type { OracleConfig } from "./config.js";
import { readOracleConfig } from "./config.js";

oracledb.fetchAsString = [oracledb.CLOB];
oracledb.autoCommit = true;

export async function createOraclePool(config: OracleConfig = readOracleConfig()): Promise<oracledb.Pool> {
  return oracledb.createPool({
    user: config.user,
    password: config.password,
    connectString: config.connectString,
    ...(config.walletLocation ? { walletLocation: config.walletLocation } : {}),
    ...(config.walletPassword ? { walletPassword: config.walletPassword } : {}),
    poolMin: 0,
    poolMax: 4,
    poolIncrement: 1,
  });
}

export async function checkOracleConnection(): Promise<string> {
  const pool = await createOraclePool();
  let connection: oracledb.Connection | undefined;
  try {
    connection = await pool.getConnection();
    const result = await connection.execute<unknown[]>(
      `SELECT SYS_CONTEXT('USERENV', 'SERVICE_NAME'), SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA') FROM dual`
    );
    const [serviceName, schemaName] = result.rows?.[0] ?? ["unknown service", "unknown schema"];
    return `Connected to ${String(serviceName)} as ${String(schemaName)}`;
  } finally {
    if (connection) await connection.close();
    await pool.close(0);
  }
}
