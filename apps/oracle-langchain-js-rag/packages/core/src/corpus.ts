import { existsSync, readdirSync, readFileSync } from "node:fs";
import { basename, resolve } from "node:path";

import { Document } from "@langchain/core/documents";

interface KnowledgeBaseMetadata {
  title: string;
  source: string;
  category: string;
  product: string;
  priority: string;
  audience: string;
  tags: string[];
}

const fallbackKnowledgeBase: Record<string, string> = {
  "oraclevs-setup.md": `---
title: OracleVS setup in TypeScript
source: oraclevs-setup
category: setup
product: LangChain.js
priority: high
audience: developer
tags: oraclevs, setup, typescript
---

# OracleVS setup in TypeScript

OracleVS lets a LangChain.js application use Oracle AI Database as a vector store.

## Install packages

Install @oracle/langchain-oracledb, oracledb, @langchain/core, and a model package such as @langchain/openai.

## Seed vectors

Use OracleVS.fromDocuments to insert LangChain Document objects, embeddings, and metadata into Oracle AI Database.
`,
  "oracle-errors.md": `---
title: Common Oracle connection errors
source: oracle-errors
category: troubleshooting
product: Oracle Database
priority: high
audience: developer
tags: ora-28001, ora-01017, connection
---

# Common Oracle connection errors

Use the database error code to decide whether the issue is credentials, service name, account status, or networking.

## ORA-28001

ORA-28001 means the account password has expired. Connect as an administrator and reset the schema password before retrying the TypeScript application.

## ORA-01017

ORA-01017 means the username/password pair is invalid for the service you connected to. Check the container port, service name, user, and password together.
`,
  "retrieval-patterns.md": `---
title: Retrieval patterns
source: retrieval-patterns
category: retrieval
product: OracleVS
priority: high
audience: developer
tags: similarity, mmr, metadata
---

# Retrieval patterns

LangChain.js can retrieve from OracleVS with similarity search, scores, metadata filters, and maximal marginal relevance.

## Similarity with score

Use similaritySearchWithScore when the UI should show distance values next to each retrieved chunk.

## Maximal marginal relevance

Use maxMarginalRelevanceSearch when the answer needs diverse context instead of several near-duplicate chunks.

## Metadata filters

Use metadata filters to restrict retrieval by category, product, audience, tenant, priority, or source.
`,
};

function slugFromFile(fileName: string): string {
  return basename(fileName).replace(/\.md$/i, "");
}

function parseList(value: string | undefined): string[] {
  if (!value) return [];
  return value
    .replace(/^\[/, "")
    .replace(/\]$/, "")
    .split(",")
    .map((item) => item.trim().replace(/^["']|["']$/g, ""))
    .filter(Boolean);
}

function parseScalarFrontmatter(frontmatter: string): Partial<KnowledgeBaseMetadata> {
  const metadata: Record<string, string> = {};
  for (const line of frontmatter.split(/\r?\n/)) {
    const match = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
    const key = match?.[1];
    const value = match?.[2];
    if (key && value !== undefined) {
      metadata[key] = value.trim().replace(/^["']|["']$/g, "");
    }
  }

  return {
    title: metadata.title,
    source: metadata.source,
    category: metadata.category,
    product: metadata.product,
    priority: metadata.priority,
    audience: metadata.audience,
    tags: parseList(metadata.tags),
  };
}

export function parseKnowledgeBaseMarkdown(markdown: string): {
  metadata: KnowledgeBaseMetadata;
  body: string;
} {
  const frontmatterMatch = markdown.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?/);
  const rawMetadata = frontmatterMatch ? parseScalarFrontmatter(frontmatterMatch[1] ?? "") : {};
  const body = frontmatterMatch ? markdown.slice(frontmatterMatch[0].length).trim() : markdown.trim();

  return {
    metadata: {
      title: rawMetadata.title ?? "Untitled knowledge base article",
      source: rawMetadata.source ?? "knowledge-base",
      category: rawMetadata.category ?? "general",
      product: rawMetadata.product ?? "Oracle AI Database",
      priority: rawMetadata.priority ?? "medium",
      audience: rawMetadata.audience ?? "developer",
      tags: rawMetadata.tags ?? [],
    },
    body,
  };
}

function sectionize(body: string): Array<{ section: string; content: string }> {
  const normalized = body.replace(/\r\n/g, "\n");
  const lines = normalized.split("\n");
  const sections: Array<{ section: string; content: string[] }> = [{ section: "Overview", content: [] }];

  for (const line of lines) {
    const heading = line.match(/^##\s+(.+)$/);
    const sectionTitle = heading?.[1];
    if (sectionTitle) {
      sections.push({ section: sectionTitle.trim(), content: [line] });
    } else {
      sections[sections.length - 1]?.content.push(line);
    }
  }

  return sections
    .map((section) => ({
      section: section.section,
      content: section.content.join("\n").replace(/^# .+\n?/, "").trim(),
    }))
    .filter((section) => section.content.length > 0);
}

export function splitKnowledgeBaseMarkdown(fileName: string, markdown: string): Document[] {
  const parsed = parseKnowledgeBaseMarkdown(markdown);
  const source = parsed.metadata.source || slugFromFile(fileName);

  return sectionize(parsed.body).map((section, index) => {
    const titleLine = `${parsed.metadata.title} - ${section.section}`;
    return new Document({
      pageContent: `${titleLine}\n\n${section.content}`,
      metadata: {
        ...parsed.metadata,
        source,
        section: section.section,
        chunk: index + 1,
      },
    });
  });
}

function knowledgeBaseDirectories(): string[] {
  const configured = process.env.KNOWLEDGE_BASE_DIR;
  return [
    ...(configured ? [configured] : []),
    resolve(process.cwd(), "samples", "knowledge-base"),
    resolve(process.cwd(), "..", "..", "samples", "knowledge-base"),
    resolve(process.cwd(), "..", "..", "..", "samples", "knowledge-base"),
  ];
}

function loadKnowledgeBaseFiles(): Array<{ fileName: string; markdown: string }> {
  const directory = knowledgeBaseDirectories().find((candidate) => existsSync(candidate));
  if (!directory) {
    return Object.entries(fallbackKnowledgeBase).map(([fileName, markdown]) => ({ fileName, markdown }));
  }

  return readdirSync(directory)
    .filter((fileName) => fileName.endsWith(".md"))
    .sort()
    .map((fileName) => ({
      fileName,
      markdown: readFileSync(resolve(directory, fileName), "utf8"),
    }));
}

export function demoDocuments(): Document[] {
  return loadKnowledgeBaseFiles().flatMap(({ fileName, markdown }) =>
    splitKnowledgeBaseMarkdown(fileName, markdown)
  );
}

export const demoQuestions = [
  "How do I use OracleVS with LangChain.js in a TypeScript RAG app?",
  "How do metadata filters improve retrieval in OracleVS?",
  "How should I fix ORA-28001 when running this Node.js sample?",
  "When should I use MMR instead of similarity search?",
];
