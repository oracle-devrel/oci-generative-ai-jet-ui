import type { EmbeddingsInterface } from "@langchain/core/embeddings";
import type { Document } from "@langchain/core/documents";
import {
  createIndex,
  DistanceStrategy,
  dropTablePurge,
  OracleVS,
  VectorElementFormat,
} from "@oracle/langchain-oracledb";
import type oracledb from "oracledb";

import type { TableInspection, WorkflowStep } from "@oracle-langchain-js-rag/shared";

import type { DemoConfig } from "./config.js";

export async function tableExists(connection: oracledb.Connection, tableName: string): Promise<boolean> {
  const result = await connection.execute<unknown[]>(
    `SELECT COUNT(*) FROM user_tables WHERE table_name = :tableName`,
    [tableName.toUpperCase()]
  );
  return Number(result.rows?.[0]?.[0] ?? 0) > 0;
}

export async function tableRowCount(connection: oracledb.Connection, tableName: string): Promise<number> {
  const result = await connection.execute<unknown[]>(`SELECT COUNT(*) FROM ${tableName}`);
  return Number(result.rows?.[0]?.[0] ?? 0);
}

export async function dropVectorTable(
  connection: oracledb.Connection,
  tableName: string
): Promise<boolean> {
  if (!(await tableExists(connection, tableName))) return false;
  await dropTablePurge(connection, tableName);
  return true;
}

export async function runTablePreflight(
  connection: oracledb.Connection,
  summary: WorkflowStep[]
): Promise<void> {
  const diagTable = "LC_JS_RAG_PREFLIGHT";
  try {
    await connection.execute(`DROP TABLE ${diagTable} PURGE`);
  } catch (error) {
    if (!String((error as Error).message).includes("ORA-00942")) throw error;
  }

  await connection.execute(`CREATE TABLE ${diagTable} (id NUMBER PRIMARY KEY, note VARCHAR2(120))`);
  await connection.execute(`INSERT INTO ${diagTable} VALUES (1, 'table permission check')`);
  const rows = await connection.execute<unknown[]>(`SELECT COUNT(*) FROM ${diagTable}`);
  await connection.execute(`DROP TABLE ${diagTable} PURGE`);

  summary.push({
    step: "table_operations",
    status: "PASS",
    detail: `Created, inserted, selected ${String(rows.rows?.[0]?.[0] ?? 0)} row, and dropped a test table`,
  });
}

export async function inspectVectorTable(
  connection: oracledb.Connection,
  tableName: string
): Promise<TableInspection> {
  const tableCount = await connection.execute<unknown[]>(`SELECT COUNT(*) FROM ${tableName}`);
  const columnRows = await connection.execute<unknown[]>(
    `SELECT column_name, data_type
     FROM user_tab_columns
     WHERE table_name = :tableName
     ORDER BY column_id`,
    [tableName]
  );
  const indexRows = await connection.execute<unknown[]>(
    `SELECT index_name, index_type
     FROM user_indexes
     WHERE table_name = :tableName
     ORDER BY index_name`,
    [tableName]
  );

  const columns = (columnRows.rows ?? []) as unknown[][];
  const indexes = (indexRows.rows ?? []) as unknown[][];

  return {
    rowCount: Number(tableCount.rows?.[0]?.[0] ?? 0),
    columns: columns.map(([column, type]) => ({
      column: String(column),
      type: String(type),
    })),
    indexes: indexes.map(([index, type]) => {
      const indexName = String(index);
      const indexType = String(type);
      const isVectorIndex =
        indexName.endsWith("_HNSW_IDX") ||
        indexName.endsWith("_IVF_IDX") ||
        indexType.toUpperCase().includes("VECTOR");
      return {
        index: indexName,
        type: indexType,
        category: isVectorIndex ? "vector" : "internal/system",
      };
    }),
  };
}

export function createVectorStore(
  pool: oracledb.Pool,
  embeddings: EmbeddingsInterface,
  config: DemoConfig
): OracleVS {
  return new OracleVS(embeddings, {
    client: pool,
    tableName: config.tableName,
    query: "Oracle AI Database LangChain.js RAG",
    distanceStrategy: DistanceStrategy.COSINE,
    format: VectorElementFormat.FLOAT32,
    description: "LangChain.js RAG sample app table for Oracle AI Database",
  });
}

export async function seedVectorStore(
  pool: oracledb.Pool,
  connection: oracledb.Connection,
  documents: Document[],
  embeddings: EmbeddingsInterface,
  config: DemoConfig,
  summary: WorkflowStep[]
): Promise<OracleVS> {
  await runTablePreflight(connection, summary);

  if (await tableExists(connection, config.tableName)) {
    await dropTablePurge(connection, config.tableName);
    summary.push({
      step: "reset_vector_store",
      status: "PASS",
      detail: `Dropped existing ${config.tableName}`,
    });
  } else {
    summary.push({
      step: "reset_vector_store",
      status: "PASS",
      detail: `${config.tableName} did not exist before this run`,
    });
  }

  const vectorStore = await OracleVS.fromDocuments(documents, embeddings, {
    client: pool,
    tableName: config.tableName,
    query: "Oracle AI Database LangChain.js RAG",
    distanceStrategy: DistanceStrategy.COSINE,
    format: VectorElementFormat.FLOAT32,
    description: "LangChain.js RAG sample app table for Oracle AI Database",
  });

  summary.push({
    step: "oraclevs_ingest",
    status: "PASS",
    detail: `Inserted ${documents.length} documents into ${config.tableName}`,
  });

  if (config.createVectorIndex) {
    try {
      const indexName = `${config.tableName}_HNSW_IDX`;
      await createIndex(connection, vectorStore, {
        idxName: indexName,
        idxType: "HNSW",
        accuracy: 90,
        parallel: 1,
      });
      summary.push({
        step: "vector_index",
        status: "PASS",
        detail: `Created or reused ${indexName}`,
      });
    } catch (error) {
      const firstLine = String((error as Error).message ?? error).split("\n")[0] ?? "unknown error";
      summary.push({
        step: "vector_index",
        status: "OPTIONAL",
        detail: `Vector index skipped: ${firstLine.slice(0, 180)}`,
      });
    }
  } else {
    summary.push({
      step: "vector_index",
      status: "READY",
      detail: "Set ORACLE_CREATE_VECTOR_INDEX=true to create an HNSW vector index when supported",
    });
  }

  return vectorStore;
}
