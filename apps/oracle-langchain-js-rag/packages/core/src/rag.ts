import { HumanMessage, SystemMessage } from "@langchain/core/messages";
import type { DocumentInterface } from "@langchain/core/documents";
import { ChatOpenAI } from "@langchain/openai";

import {
  createOraclePool,
  createVectorStore,
  dropVectorTable,
  inspectVectorTable,
  missingOracleEnv,
  readDemoConfig,
  seedVectorStore,
  tableExists,
  tableRowCount,
} from "@oracle-langchain-js-rag/db";
import type {
  AskResponse,
  CorpusResponse,
  OracleInspectionResponse,
  RagTrace,
  ResetResponse,
  RetrievedDocument,
  RetrievalMode,
  SeedResponse,
  WorkflowStep,
} from "@oracle-langchain-js-rag/shared";

import { demoDocuments } from "./corpus.js";
import { DemoEmbeddings } from "./demoEmbeddings.js";

function parseMetadata(metadata: unknown): Record<string, unknown> {
  if (typeof metadata === "string") {
    try {
      const parsed = JSON.parse(metadata) as unknown;
      return parsed && typeof parsed === "object" && !Array.isArray(parsed)
        ? (parsed as Record<string, unknown>)
        : {};
    } catch {
      return {};
    }
  }
  return metadata && typeof metadata === "object" && !Array.isArray(metadata)
    ? (metadata as Record<string, unknown>)
    : {};
}

function textValue(metadata: Record<string, unknown>, key: string): string {
  const value = metadata[key];
  return typeof value === "string" ? value : "";
}

function arrayValue(metadata: Record<string, unknown>, key: string): string[] {
  const value = metadata[key];
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function snippet(text: string): string {
  return text.length > 260 ? `${text.slice(0, 257)}...` : text;
}

export function formatGroundingEvidence(retrieved: RetrievedDocument[]): string {
  if (retrieved.length === 0) {
    return "No OracleVS evidence was retrieved. Seed the knowledge base, loosen filters, or ask a question covered by the corpus.";
  }

  return [
    "Evidence pack for grounded generation:",
    ...retrieved.map((doc) =>
      [
        `[${doc.rank}] ${doc.title} / ${doc.section}`,
        doc.snippet,
        `Source: ${doc.source}`,
        `Metadata: category=${doc.category}; product=${doc.product}; priority=${doc.priority}; audience=${doc.audience}`,
        doc.tags.length > 0 ? `Tags: ${doc.tags.join(", ")}` : undefined,
        typeof doc.distance === "number" ? `Distance: ${doc.distance}` : undefined,
      ]
        .filter((line): line is string => Boolean(line))
        .join("\n")
    ),
  ].join("\n\n");
}

function toRetrievedDocument(
  doc: DocumentInterface,
  distance: number | undefined,
  rank: number
): RetrievedDocument {
  const metadata = parseMetadata(doc.metadata);
  return {
    rank,
    ...(typeof distance === "number" ? { distance: Number(distance.toFixed(6)) } : {}),
    source: textValue(metadata, "source"),
    title: textValue(metadata, "title"),
    section: textValue(metadata, "section"),
    category: textValue(metadata, "category"),
    product: textValue(metadata, "product"),
    priority: textValue(metadata, "priority"),
    audience: textValue(metadata, "audience"),
    tags: arrayValue(metadata, "tags"),
    snippet: snippet(doc.pageContent),
    metadata,
  };
}

export function buildRagTrace(input: {
  question: string;
  retrieved: RetrievedDocument[];
  queryVector: number[];
  k: number;
  category?: string;
  retrievalMode: RetrievalMode;
  fetchK?: number;
  tableName: string;
  usedLlm: boolean;
  llmModel: string;
}): RagTrace {
  const filter =
    input.category && input.category !== "all"
      ? `category = ${input.category}`
      : "none";

  return {
    embedding: {
      model: "DemoEmbeddings",
      dimension: input.queryVector.length,
      preview: input.queryVector.slice(0, 12).map((value) => Number(value.toFixed(6))),
      note:
        "The demo uses deterministic TypeScript embeddings so the tutorial is reproducible. Swap this class for OpenAI, OCI Generative AI, or another LangChain.js Embeddings implementation in production.",
    },
    retrieval: {
      mode: input.retrievalMode,
      tableName: input.tableName,
      topK: input.k,
      ...(input.fetchK ? { fetchK: input.fetchK } : {}),
      filter,
      distanceStrategy: "COSINE",
      langchainCall:
        input.retrievalMode === "mmr"
          ? "vectorStore.maxMarginalRelevanceSearch(question, { k, fetchK, lambda, filter })"
          : "vectorStore.similaritySearchWithScore(question, k, filter)",
      representativeSql:
        `SELECT id, text, metadata, VECTOR_DISTANCE(embedding, :query_vector, COSINE) AS distance\n` +
        `FROM ${input.tableName}\n` +
        `${filter === "none" ? "" : "WHERE JSON_VALUE(metadata, '$.category') = :category\n"}` +
        `ORDER BY distance\nFETCH FIRST :k ROWS ONLY`,
    },
    generation: {
      mode: input.usedLlm ? "LLM grounded answer" : "Extractive answer",
      model: input.usedLlm ? input.llmModel : "none",
      systemInstruction:
        "Answer as a developer assistant using only retrieved OracleVS context. Include concrete fix steps and cite source chunks.",
    },
    context: formatGroundingEvidence(input.retrieved),
  };
}

async function buildAnswer(
  question: string,
  retrieved: RetrievedDocument[],
  apiKey: string | undefined,
  model: string
): Promise<{ answer: string; usedLlm: boolean }> {
  const context = formatGroundingEvidence(retrieved);

  if (!apiKey) {
    return {
      usedLlm: false,
      answer:
        `No OPENAI_API_KEY is configured, so the assistant returned a grounded extractive answer.\n\n` +
        `Question: ${question}\n\n` +
        `Top OracleVS context:\n${context}\n\n` +
        `Use this context to explain the issue, list fix steps, and cite the retrieved sources.`,
    };
  }

  const chat = new ChatOpenAI({
    apiKey,
    model,
    temperature: 0,
  });

  const response = await chat.invoke([
    new SystemMessage(
      "You are a concise TypeScript developer assistant for Oracle AI Database and LangChain.js. Answer only from the retrieved OracleVS context. Include practical fix steps or code guidance when relevant. Cite source chunks by rank such as [1] or [2]. If the context is insufficient, say what is missing."
    ),
    new HumanMessage(`Question: ${question}\n\nRetrieved context:\n${context}`),
  ]);

  return {
    usedLlm: true,
    answer: typeof response.content === "string" ? response.content : JSON.stringify(response.content),
  };
}

export function getDemoCorpus(): CorpusResponse {
  const documents = demoDocuments().map((doc, index) => {
    const metadata = parseMetadata(doc.metadata);
    return {
      id: `doc-${String(index + 1).padStart(2, "0")}`,
      source: textValue(metadata, "source"),
      title: textValue(metadata, "title"),
      section: textValue(metadata, "section"),
      category: textValue(metadata, "category"),
      product: textValue(metadata, "product"),
      priority: textValue(metadata, "priority"),
      audience: textValue(metadata, "audience"),
      tags: arrayValue(metadata, "tags"),
      content: doc.pageContent,
      metadata,
    };
  });
  const sources = new Set(documents.map((doc) => doc.source));

  return {
    documents,
    totalDocuments: documents.length,
    totalSources: sources.size,
    embeddingModel: "DemoEmbeddings",
    embeddingDimension: 12,
    chunkingStrategy: "Markdown files split into section-level LangChain Document chunks",
  };
}

export async function inspectOracleDemoTable(): Promise<OracleInspectionResponse> {
  const config = readDemoConfig();
  const pool = await createOraclePool();
  const connection = await pool.getConnection();

  try {
    if (!(await tableExists(connection, config.tableName))) {
      return {
        tableName: config.tableName,
        connected: true,
        detail: `${config.tableName} does not exist yet. Run Seed to create the OracleVS table.`,
      };
    }

    return {
      tableName: config.tableName,
      connected: true,
      detail: `${config.tableName} is available in Oracle AI Database`,
      inspection: await inspectVectorTable(connection, config.tableName),
    };
  } finally {
    await connection.close();
    await pool.close(0);
  }
}

export async function seedDemoCorpus(): Promise<SeedResponse> {
  const config = readDemoConfig();
  const documents = demoDocuments();
  const summary: WorkflowStep[] = [];
  const pool = await createOraclePool();
  const connection = await pool.getConnection();

  try {
    await seedVectorStore(pool, connection, documents, new DemoEmbeddings(), config, summary);
    const inspection = await inspectVectorTable(connection, config.tableName);
    return {
      tableName: config.tableName,
      documentsIndexed: documents.length,
      inspection,
      summary,
    };
  } finally {
    await connection.close();
    await pool.close(0);
  }
}

export async function resetDemoTable(): Promise<ResetResponse> {
  const config = readDemoConfig();
  const pool = await createOraclePool();
  const connection = await pool.getConnection();

  try {
    const dropped = await dropVectorTable(connection, config.tableName);
    return {
      tableName: config.tableName,
      dropped,
      detail: dropped ? `Dropped ${config.tableName}` : `${config.tableName} did not exist`,
    };
  } finally {
    await connection.close();
    await pool.close(0);
  }
}

export async function askOracleRag(
  question: string,
  options: { k?: number; category?: string; retrievalMode?: RetrievalMode } = {}
): Promise<AskResponse> {
  const config = readDemoConfig();
  const summary: WorkflowStep[] = [];
  const pool = await createOraclePool();
  const connection = await pool.getConnection();

  try {
    if (!(await tableExists(connection, config.tableName))) {
      throw new Error(`Table ${config.tableName} does not exist. Run pnpm seed or use the Seed button first.`);
    }

    const rowCount = await tableRowCount(connection, config.tableName);
    if (rowCount === 0) {
      throw new Error(`Table ${config.tableName} is empty. Run pnpm seed or use the Seed button first.`);
    }

    summary.push({
      step: "oraclevs_ready",
      status: "PASS",
      detail: `${config.tableName} contains ${rowCount} documents`,
    });

    const vectorStore = createVectorStore(pool, new DemoEmbeddings(), config);
    await vectorStore.initialize();

    const k = Math.min(Math.max(options.k ?? 4, 1), 8);
    const retrievalMode = options.retrievalMode ?? "similarity";
    const fetchK = Math.max(k * 2, 8);
    const filter =
      options.category && options.category !== "all"
        ? { category: { $eq: options.category } }
        : undefined;

    const retrieved =
      retrievalMode === "mmr"
        ? (await vectorStore.maxMarginalRelevanceSearch(question, {
            k,
            fetchK,
            lambda: 0.5,
            filter,
          })).map((doc, index) => toRetrievedDocument(doc, undefined, index + 1))
        : (await vectorStore.similaritySearchWithScore(question, k, filter)).map(([doc, distance], index) =>
            toRetrievedDocument(doc, distance, index + 1)
          );
    const queryVector = await new DemoEmbeddings().embedQuery(question);

    summary.push({
      step: retrievalMode === "mmr" ? "mmr_search" : "similarity_search",
      status: "PASS",
      detail:
        retrievalMode === "mmr"
          ? `Retrieved ${retrieved.length} diverse chunks with fetchK=${fetchK}${options.category ? ` and category=${options.category}` : ""}`
          : `Retrieved ${retrieved.length} chunks with scores${options.category ? ` and category=${options.category}` : ""}`,
    });

    const answer = await buildAnswer(question, retrieved, config.openAiApiKey, config.llmModel);
    const trace = buildRagTrace({
      question,
      retrieved,
      queryVector,
      k,
      category: options.category,
      retrievalMode,
      fetchK: retrievalMode === "mmr" ? fetchK : undefined,
      tableName: config.tableName,
      usedLlm: answer.usedLlm,
      llmModel: config.llmModel,
    });

    summary.push({
      step: "rag_answer",
      status: "PASS",
      detail: answer.usedLlm
        ? `Generated answer with ${config.llmModel}`
        : "Returned extractive answer because OPENAI_API_KEY is not configured",
    });

    return {
      question,
      answer: answer.answer,
      tableName: config.tableName,
      retrievalMode,
      usedLlm: answer.usedLlm,
      retrieved,
      summary,
      trace,
    };
  } finally {
    await connection.close();
    await pool.close(0);
  }
}

export function getSetupState() {
  const config = readDemoConfig();
  const missingOracleVars = missingOracleEnv();
  return {
    tableName: config.tableName,
    createVectorIndex: config.createVectorIndex,
    openAiConfigured: Boolean(config.openAiApiKey),
    oracleConfigured: missingOracleVars.length === 0,
    missingOracleVars,
  };
}
