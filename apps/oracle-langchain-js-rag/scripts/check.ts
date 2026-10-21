import "dotenv/config";

import { getSetupState } from "@oracle-langchain-js-rag/core";
import { checkOracleConnection } from "@oracle-langchain-js-rag/db";

async function main() {
  const setup = getSetupState();
  console.log(`Table: ${setup.tableName}`);
  console.log(`OpenAI configured: ${setup.openAiConfigured ? "yes" : "no"}`);
  console.log(`Vector index requested: ${setup.createVectorIndex ? "yes" : "no"}`);

  if (!setup.oracleConfigured) {
    throw new Error(`Missing Oracle environment variables: ${setup.missingOracleVars.join(", ")}`);
  }

  console.log(await checkOracleConnection());
}

main().catch((error) => {
  console.error("db:check failed:", error);
  process.exit(1);
});
