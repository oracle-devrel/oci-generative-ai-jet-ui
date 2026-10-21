import { describe, expect, it } from "vitest";

import { demoQuestions, parseKnowledgeBaseMarkdown, splitKnowledgeBaseMarkdown } from "./corpus.js";

const sample = `---
title: OracleVS setup
source: oraclevs-setup
category: setup
product: LangChain.js
priority: high
audience: developer
tags: oraclevs, setup, typescript
---

# OracleVS setup

Use OracleVS as the vector store for a TypeScript RAG app.

## Install packages

Install @oracle/langchain-oracledb and oracledb.

## Seed vectors

Use OracleVS.fromDocuments to insert text, embeddings, and metadata.
`;

describe("knowledge base corpus", () => {
  it("parses markdown frontmatter into typed metadata", () => {
    const parsed = parseKnowledgeBaseMarkdown(sample);

    expect(parsed.metadata.title).toBe("OracleVS setup");
    expect(parsed.metadata.category).toBe("setup");
    expect(parsed.metadata.tags).toEqual(["oraclevs", "setup", "typescript"]);
    expect(parsed.body).toContain("Use OracleVS as the vector store");
  });

  it("splits source files into section-level LangChain documents", () => {
    const documents = splitKnowledgeBaseMarkdown("oraclevs-setup.md", sample);

    expect(documents).toHaveLength(3);
    expect(documents[0]?.metadata.source).toBe("oraclevs-setup");
    expect(documents[1]?.metadata.section).toBe("Install packages");
    expect(documents[2]?.pageContent).toContain("OracleVS.fromDocuments");
  });

  it("uses developer-assistant sample questions", () => {
    expect(demoQuestions.some((question) => question.includes("ORA-28001"))).toBe(true);
    expect(demoQuestions.some((question) => question.includes("metadata filters"))).toBe(true);
  });
});
