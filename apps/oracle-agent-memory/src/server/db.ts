import oracledb from 'oracledb';

let pool: oracledb.Pool | null = null;

export async function initDb(): Promise<void> {
  if (pool) return;
  oracledb.fetchAsString = [oracledb.CLOB];
  pool = await oracledb.createPool({
    user: process.env.ORACLE_USER!,
    password: process.env.ORACLE_PASSWORD!,
    connectString: process.env.ORACLE_CONNECT_STRING!,
    poolMin: 2,
    poolMax: 10,
  });
}

export async function closeDb(): Promise<void> {
  if (pool) {
    await pool.close(10);
    pool = null;
  }
}

export async function withConn<T>(
  fn: (conn: oracledb.Connection) => Promise<T>,
): Promise<T> {
  if (!pool) throw new Error('DB pool not initialized — call initDb() first');
  const conn = await pool.getConnection();
  try {
    return await fn(conn);
  } finally {
    await conn.close();
  }
}

export { oracledb };
