import "dotenv/config";

import { seedDemoCorpus } from "@oracle-langchain-js-rag/core";

async function main() {
  const result = await seedDemoCorpus();
  console.log(`Seeded ${result.documentsIndexed} documents into ${result.tableName}`);
  for (const step of result.summary) {
    console.log(`${step.status.padEnd(8)} ${step.step}: ${step.detail}`);
  }
}

main().catch((error) => {
  console.error("seed failed:", error);
  process.exit(1);
});
