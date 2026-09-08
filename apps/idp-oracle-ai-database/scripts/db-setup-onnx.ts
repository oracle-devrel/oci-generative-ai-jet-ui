import "dotenv/config";
import oracledb from "oracledb";
import { EMBEDDING_MODEL_NAME } from "@idp/shared";

const ONNX_URL =
  process.env.ONNX_MODEL_URL ??
  "https://adwc4pm.objectstorage.us-ashburn-1.oci.customer-oci.com/p/iPX9W0MZeRkwJKWdFmdJCemmN-iKAl_bFvNGYLW7YqIrw4kKsukL24J2q93Beb9S/n/adwc4pm/b/OML-ai-models/o/all_MiniLM_L12_v2.onnx";
const FILE_NAME = process.env.ONNX_MODEL_FILE ?? "all_MiniLM_L12_v2.onnx";

function adminConnection(): oracledb.ConnectionAttributes {
  return {
    user: "ADMIN",
    password: process.env.ORACLE_ADMIN_PASSWORD ?? process.env.ORACLE_PASSWORD!,
    connectString: process.env.ORACLE_CONNECT_STRING!,
    walletLocation: process.env.ORACLE_WALLET_LOCATION,
    walletPassword: process.env.ORACLE_WALLET_PASSWORD,
  };
}

function idpConnection(): oracledb.ConnectionAttributes {
  return {
    user: process.env.ORACLE_USER!,
    password: process.env.ORACLE_PASSWORD!,
    connectString: process.env.ORACLE_CONNECT_STRING!,
    walletLocation: process.env.ORACLE_WALLET_LOCATION,
    walletPassword: process.env.ORACLE_WALLET_PASSWORD,
  };
}

async function main() {
  const required = [
    "ORACLE_CONNECT_STRING",
    "ORACLE_USER",
    "ORACLE_PASSWORD",
    "ORACLE_ADMIN_PASSWORD",
  ];
  for (const name of required) {
    if (!process.env[name]) throw new Error(`${name} env var is required`);
  }

  console.log(`Phase 1: ADMIN pulls ${FILE_NAME} into DATA_PUMP_DIR`);
  const adminConn = await oracledb.getConnection(adminConnection());
  adminConn.callTimeout = 300_000;
  try {
    await adminConn.execute(
      `BEGIN
         DBMS_CLOUD.GET_OBJECT(
           object_uri      => :url,
           directory_name  => 'DATA_PUMP_DIR',
           file_name       => :fname
         );
       END;`,
      { url: ONNX_URL, fname: FILE_NAME }
    );
    const list = await adminConn.execute<{ OBJECT_NAME: string; BYTES: number }>(
      `SELECT object_name, bytes FROM dbms_cloud.list_files('DATA_PUMP_DIR') WHERE object_name = :fname`,
      { fname: FILE_NAME },
      { outFormat: oracledb.OUT_FORMAT_OBJECT }
    );
    const row = list.rows?.[0];
    if (!row) throw new Error(`${FILE_NAME} not visible in DATA_PUMP_DIR after download`);
    console.log(`  ✓ ${row.OBJECT_NAME} = ${row.BYTES} bytes`);
  } finally {
    await adminConn.close();
  }

  console.log(
    `\nPhase 2: ${process.env.ORACLE_USER} loads "${EMBEDDING_MODEL_NAME}" from DATA_PUMP_DIR`
  );
  const conn = await oracledb.getConnection(idpConnection());
  conn.callTimeout = 300_000;
  try {
    try {
      await conn.execute(
        `BEGIN DBMS_VECTOR.DROP_ONNX_MODEL(model_name => :name, force => TRUE); END;`,
        { name: EMBEDDING_MODEL_NAME }
      );
      console.log(`  · dropped existing model ${EMBEDDING_MODEL_NAME}`);
    } catch (err) {
      const code = (err as { errorNum?: number }).errorNum;
      if (code !== 40286) throw err;
    }

    await conn.execute(
      `BEGIN
         DBMS_VECTOR.LOAD_ONNX_MODEL(
           directory  => 'DATA_PUMP_DIR',
           file_name  => :file,
           model_name => :model
         );
       END;`,
      { file: FILE_NAME, model: EMBEDDING_MODEL_NAME }
    );
    console.log(`  ✓ model ${EMBEDDING_MODEL_NAME} loaded`);

    const r = await conn.execute<{ DIM: number }>(
      `SELECT VECTOR_DIMENSION_COUNT(VECTOR_EMBEDDING(${EMBEDDING_MODEL_NAME} USING 'hello world' AS data)) AS DIM FROM DUAL`,
      {},
      { outFormat: oracledb.OUT_FORMAT_OBJECT }
    );
    console.log(`  ✓ embedding dimension = ${r.rows?.[0]?.DIM}`);
  } finally {
    await conn.close();
  }
}

main().catch((err) => {
  console.error("db-setup-onnx failed:", err.message ?? err);
  process.exit(1);
});
