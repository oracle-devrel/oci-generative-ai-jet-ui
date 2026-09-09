import "dotenv/config";
import { readFile } from "node:fs/promises";
import oracledb from "oracledb";

const CREDENTIAL_NAME = "OCI_CRED";

function connection(user: string, password: string): oracledb.ConnectionAttributes {
  return {
    user,
    password,
    connectString: process.env.ORACLE_CONNECT_STRING!,
    walletLocation: process.env.ORACLE_WALLET_LOCATION,
    walletPassword: process.env.ORACLE_WALLET_PASSWORD,
  };
}

async function main() {
  const required = [
    "ORACLE_ADMIN_PASSWORD",
    "ORACLE_USER",
    "ORACLE_PASSWORD",
    "OCI_USER_OCID",
    "OCI_TENANCY_OCID",
    "OCI_COMPARTMENT_OCID",
    "OCI_FINGERPRINT",
    "OCI_PRIVATE_KEY_PATH",
  ];
  for (const name of required) {
    if (!process.env[name]) throw new Error(`${name} env var is required`);
  }

  const idpUser = process.env.ORACLE_USER!;
  const adminPassword = process.env.ORACLE_ADMIN_PASSWORD!;
  const idpPassword = process.env.ORACLE_PASSWORD!;

  console.log(`Phase 1: ADMIN grants privileges to ${idpUser}`);
  const adminConn = await oracledb.getConnection(connection("ADMIN", adminPassword));
  try {
    for (const stmt of [
      `GRANT CREATE CREDENTIAL TO ${idpUser}`,
      `GRANT EXECUTE ON DBMS_CLOUD TO ${idpUser}`,
      `GRANT EXECUTE ON DBMS_CLOUD_AI TO ${idpUser}`,
      `BEGIN DBMS_NETWORK_ACL_ADMIN.APPEND_HOST_ACE(
         host => 'inference.generativeai.${process.env.OCI_GENAI_REGION ?? "eu-frankfurt-1"}.oci.oraclecloud.com',
         ace  => xs$ace_type(privilege_list => xs$name_list('http'),
                             principal_name => '${idpUser}',
                             principal_type => xs_acl.ptype_db));
       END;`,
    ]) {
      try {
        await adminConn.execute(stmt);
        console.log(`  ✓ ${stmt.slice(0, 70).replace(/\s+/g, " ")}…`);
      } catch (err) {
        const code = (err as { errorNum?: number }).errorNum;
        if (code === 1031 || code === 1917 || code === 31003) {
          console.log(`  · already in place (ORA-${code})`);
        } else {
          throw err;
        }
      }
    }
  } finally {
    await adminConn.close();
  }

  console.log(`\nPhase 2: ${idpUser} registers credential "${CREDENTIAL_NAME}"`);
  const pem = await readFile(process.env.OCI_PRIVATE_KEY_PATH!, "utf-8");
  const privateKey = pem
    .replace(/-----BEGIN [^-]+-----/g, "")
    .replace(/-----END [^-]+-----/g, "")
    .replace(/\r?\n/g, "")
    .trim();

  const credentialPayload = {
    user_ocid: process.env.OCI_USER_OCID!,
    tenancy_ocid: process.env.OCI_TENANCY_OCID!,
    compartment_ocid: process.env.OCI_COMPARTMENT_OCID!,
    private_key: privateKey,
    fingerprint: process.env.OCI_FINGERPRINT!,
  };

  const conn = await oracledb.getConnection(connection(idpUser, idpPassword));
  try {
    try {
      await conn.execute(
        `BEGIN DBMS_VECTOR_CHAIN.DROP_CREDENTIAL(credential_name => :name); END;`,
        { name: CREDENTIAL_NAME }
      );
      console.log(`  · dropped existing credential ${CREDENTIAL_NAME}`);
    } catch {
      // ignore: probably didn't exist yet
    }

    await conn.execute(
      `BEGIN
         DBMS_VECTOR_CHAIN.CREATE_CREDENTIAL(
           credential_name => :name,
           params          => JSON(:payload)
         );
       END;`,
      { name: CREDENTIAL_NAME, payload: JSON.stringify(credentialPayload) }
    );
    console.log(`  ✓ credential ${CREDENTIAL_NAME} created`);

    const region = process.env.OCI_GENAI_REGION ?? "eu-frankfurt-1";
    const model = process.env.OCI_GENAI_MODEL ?? "meta.llama-3.3-70b-instruct";
    const url = `https://inference.generativeai.${region}.oci.oraclecloud.com/20231130/actions/chat`;
    const smokeParams = JSON.stringify({
      provider: "ocigenai",
      credential_name: CREDENTIAL_NAME,
      url,
      model,
      chatRequest: { maxTokens: 32, temperature: 0 },
    });

    console.log(`\nPhase 3: smoke test UTL_TO_GENERATE_TEXT against ${model} in ${region}`);
    const result = await conn.execute<{ OUT: string }>(
      `SELECT DBMS_VECTOR_CHAIN.UTL_TO_GENERATE_TEXT(:input, JSON(:params)) AS OUT FROM DUAL`,
      { input: "Reply with the single word PONG.", params: smokeParams },
      {
        outFormat: oracledb.OUT_FORMAT_OBJECT,
        fetchInfo: { OUT: { type: oracledb.STRING } },
      }
    );
    console.log(`  ✓ response: ${(result.rows?.[0]?.OUT ?? "<empty>").trim()}`);
  } finally {
    await conn.close();
  }
}

main().catch((err) => {
  console.error("credential setup failed:", err.message ?? err);
  process.exit(1);
});
