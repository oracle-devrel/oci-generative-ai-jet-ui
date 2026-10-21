export interface OracleConfig {
  user: string;
  password: string;
  connectString: string;
  walletLocation?: string;
  walletPassword?: string;
}

export interface DemoConfig {
  tableName: string;
  createVectorIndex: boolean;
  llmModel: string;
  openAiApiKey?: string;
}

function firstEnv(names: string[]): string | undefined {
  for (const name of names) {
    const value = process.env[name];
    if (value && value.trim()) return value.trim();
  }
  return undefined;
}

export function normalizeTableName(value: string | undefined): string {
  const tableName = (value || "LC_JS_RAG_DEMO").trim().toUpperCase();
  if (!/^[A-Z][A-Z0-9_]{0,127}$/.test(tableName)) {
    throw new Error(
      `Invalid Oracle table name "${tableName}". Use letters, numbers, and underscores only.`
    );
  }
  return tableName;
}

export function missingOracleEnv(): string[] {
  const required: Array<[string, string | undefined]> = [
    ["ORACLE_USER or DB_USER", firstEnv(["ORACLE_USER", "DB_USER", "ORACLEDB_USER"])],
    ["ORACLE_PASSWORD or DB_PASSWORD", firstEnv(["ORACLE_PASSWORD", "DB_PASSWORD", "ORACLEDB_PASSWORD"])],
    [
      "ORACLE_CONNECT_STRING, ORACLE_DSN, DB_CONNECT_STRING, DB_DSN, or ORACLEDB_CONNECTION_STRING",
      firstEnv(["ORACLE_CONNECT_STRING", "ORACLE_DSN", "DB_CONNECT_STRING", "DB_DSN", "ORACLEDB_CONNECTION_STRING"]),
    ],
  ];
  return required.filter(([, value]) => !value).map(([name]) => name);
}

export function readOracleConfig(): OracleConfig {
  const missing = missingOracleEnv();
  if (missing.length > 0) {
    throw new Error(`Missing required Oracle environment variables: ${missing.join(", ")}`);
  }

  const walletLocation = firstEnv(["ORACLE_WALLET_LOCATION", "TNS_ADMIN"]);
  const walletPassword = firstEnv(["ORACLE_WALLET_PASSWORD"]);

  return {
    user: firstEnv(["ORACLE_USER", "DB_USER", "ORACLEDB_USER"])!,
    password: firstEnv(["ORACLE_PASSWORD", "DB_PASSWORD", "ORACLEDB_PASSWORD"])!,
    connectString: firstEnv([
      "ORACLE_CONNECT_STRING",
      "ORACLE_DSN",
      "DB_CONNECT_STRING",
      "DB_DSN",
      "ORACLEDB_CONNECTION_STRING",
    ])!,
    ...(walletLocation ? { walletLocation } : {}),
    ...(walletPassword ? { walletPassword } : {}),
  };
}

export function readDemoConfig(): DemoConfig {
  const openAiApiKey = firstEnv(["OPENAI_API_KEY", "MODEL_PROVIDER_API_KEY"]);
  return {
    tableName: normalizeTableName(firstEnv(["ORACLE_TABLE_NAME", "LANGCHAIN_JS_TABLE"])),
    createVectorIndex:
      (firstEnv(["ORACLE_CREATE_VECTOR_INDEX", "LANGCHAIN_JS_CREATE_INDEX"]) || "false").toLowerCase() ===
      "true",
    llmModel: firstEnv(["OPENAI_MODEL", "LANGCHAIN_JS_LLM_MODEL", "OAMP_LLM_MODEL"]) || "gpt-4o-mini",
    ...(openAiApiKey ? { openAiApiKey } : {}),
  };
}
