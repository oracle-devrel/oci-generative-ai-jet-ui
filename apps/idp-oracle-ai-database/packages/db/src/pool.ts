import oracledb from "oracledb";
import { logger } from "@idp/logger";

oracledb.fetchAsString = [oracledb.CLOB];
oracledb.autoCommit = true;

export interface PoolConfig {
  connectString: string;
  user: string;
  password: string;
  walletLocation?: string;
  walletPassword?: string;
  poolMin?: number;
  poolMax?: number;
}

let pool: oracledb.Pool | null = null;

export async function createPool(config: PoolConfig): Promise<oracledb.Pool> {
  if (pool) return pool;
  pool = await oracledb.createPool({
    user: config.user,
    password: config.password,
    connectString: config.connectString,
    ...(config.walletLocation ? { walletLocation: config.walletLocation } : {}),
    ...(config.walletPassword ? { walletPassword: config.walletPassword } : {}),
    poolMin: config.poolMin ?? 0,
    poolMax: config.poolMax ?? 4,
    poolIncrement: 1,
  });
  logger.info("oracle pool created", { connectString: config.connectString });
  return pool;
}

export async function closePool(): Promise<void> {
  if (!pool) return;
  await pool.close(10);
  pool = null;
}

export async function withConnection<T>(fn: (conn: oracledb.Connection) => Promise<T>): Promise<T> {
  if (!pool) {
    throw new Error("Oracle pool not initialized. Call createPool() first.");
  }
  const conn = await pool.getConnection();
  try {
    return await fn(conn);
  } finally {
    await conn.close();
  }
}
