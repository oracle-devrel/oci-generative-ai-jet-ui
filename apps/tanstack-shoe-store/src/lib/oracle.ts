import oracledb from 'oracledb'

oracledb.fetchAsString = [oracledb.CLOB]

let pool: oracledb.Pool | null = null

export async function getPool(): Promise<oracledb.Pool> {
  if (!pool) {
    pool = await oracledb.createPool({
      user: process.env.ORACLE_USER,
      password: process.env.ORACLE_PASSWORD,
      connectionString: process.env.ORACLE_CONNECTION_STRING,
      poolMin: 1,
      poolMax: 4,
      poolIncrement: 1,
    })
  }
  return pool
}

export async function executeSelectAI(
  prompt: string,
  action: 'narrate' | 'runsql' | 'showsql' | 'chat' = 'narrate',
): Promise<string> {
  const p = await getPool()
  const connection = await p.getConnection()

  try {
    const result = await connection.execute<{ RESPONSE: string }>(
      `SELECT DBMS_CLOUD_AI.GENERATE(
        prompt       => :prompt,
        profile_name => :profile,
        action       => :action
      ) AS RESPONSE FROM DUAL`,
      {
        prompt: prompt,
        profile: process.env.ORACLE_AI_PROFILE || 'SHOESTORE_AI',
        action: action,
      },
      { outFormat: oracledb.OUT_FORMAT_OBJECT },
    )

    return result.rows?.[0]?.RESPONSE ?? 'No results returned.'
  } finally {
    await connection.close()
  }
}
