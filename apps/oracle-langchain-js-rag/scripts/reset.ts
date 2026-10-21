import "dotenv/config";

import { resetDemoTable } from "@oracle-langchain-js-rag/core";

async function main() {
  const result = await resetDemoTable();
  console.log(result.detail);
}

main().catch((error) => {
  console.error("reset failed:", error);
  process.exit(1);
});
