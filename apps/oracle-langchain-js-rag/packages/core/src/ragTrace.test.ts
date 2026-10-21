import { describe, expect, it } from "vitest";

import type { RetrievedDocument } from "@oracle-langchain-js-rag/shared";

import { buildRagTrace, formatGroundingEvidence } from "./rag.js";

const retrieved: RetrievedDocument[] = [
  {
    rank: 1,
    distance: 0.123456,
    source: "metadata-filtering",
    title: "Retrieval patterns with OracleVS",
    section: "Metadata filters",
    category: "retrieval",
    product: "OracleVS",
    priority: "high",
    audience: "developer",
    tags: ["metadata", "oraclevs"],
    snippet: "Metadata filters narrow OracleVS retrieval by source, category, tenant, priority, or audience.",
    metadata: {
      source: "metadata-filtering",
      category: "retrieval",
      product: "OracleVS",
      priority: "high",
      audience: "developer",
    },
  },
];

describe("buildRagTrace", () => {
  it("formats retrieved chunks as a clean evidence pack for the UI and LLM", () => {
    const evidence = formatGroundingEvidence(retrieved);

    expect(evidence).toContain("Evidence pack for grounded generation");
    expect(evidence).toContain("[1] Retrieval patterns with OracleVS / Metadata filters");
    expect(evidence).toContain("Metadata filters narrow OracleVS retrieval");
    expect(evidence).toContain("Source: metadata-filtering");
    expect(evidence).not.toContain("undefined");
  });

  it("explains when no retrieved chunks are available", () => {
    expect(formatGroundingEvidence([])).toBe(
      "No OracleVS evidence was retrieved. Seed the knowledge base, loosen filters, or ask a question covered by the corpus."
    );
  });

  it("explains the LangChain.js to OracleVS retrieval flow for the UI", () => {
    const trace = buildRagTrace({
      category: "retrieval",
      k: 4,
      llmModel: "gpt-4o-mini",
      queryVector: [0.12, 0.34, 0, 0.56],
      question: "How do metadata filters improve retrieval?",
      retrieved,
      retrievalMode: "similarity",
      tableName: "LC_JS_RAG_DEMO",
      usedLlm: true,
    });

    expect(trace.context).toContain("[1] Retrieval patterns with OracleVS / Metadata filters");
    expect(trace.context).toContain("Metadata filters narrow OracleVS retrieval");
    expect(trace.embedding.dimension).toBe(4);
    expect(trace.embedding.preview).toEqual([0.12, 0.34, 0, 0.56]);
    expect(trace.retrieval.filter).toBe("category = retrieval");
    expect(trace.retrieval.mode).toBe("similarity");
    expect(trace.retrieval.langchainCall).toContain("similaritySearchWithScore");
    expect(trace.retrieval.representativeSql).toContain("VECTOR_DISTANCE");
    expect(trace.generation.mode).toBe("LLM grounded answer");
  });
});
