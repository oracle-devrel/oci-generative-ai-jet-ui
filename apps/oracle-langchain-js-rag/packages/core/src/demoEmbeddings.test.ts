import { describe, expect, it } from "vitest";

import { demoDocuments } from "./corpus.js";
import { DemoEmbeddings } from "./demoEmbeddings.js";

describe("DemoEmbeddings", () => {
  it("returns normalized vectors with stable dimensions", async () => {
    const embeddings = new DemoEmbeddings();
    const vector = await embeddings.embedQuery("Oracle LangChain.js RAG retrieval");

    expect(vector).toHaveLength(12);
    expect(vector.some((value) => value > 0)).toBe(true);
    expect(Math.sqrt(vector.reduce((sum, value) => sum + value * value, 0))).toBeCloseTo(1, 4);
  });

  it("creates a demo corpus with metadata for UI filtering", () => {
    const docs = demoDocuments();

    expect(docs.length).toBeGreaterThanOrEqual(6);
    expect(docs.every((doc) => typeof doc.metadata.category === "string")).toBe(true);
    expect(docs.some((doc) => doc.metadata.category === "retrieval")).toBe(true);
  });
});
