import oracledb from "oracledb";
import { Readable } from "node:stream";
import { withConnection } from "../pool.js";
import { EMBEDDING_MODEL_NAME, type DocStatus, type DocType } from "@idp/shared";
import {
  documentRowSchema,
  documentListItemRowSchema,
  similarDocumentRowSchema,
  blobRowSchema,
  extractedTextRowSchema,
  type DocumentRow,
  type DocumentListItem,
  type SimilarDocument,
} from "../schemas.js";

export type { DocumentRow, DocumentListItem, SimilarDocument };

function uuidHex(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0"))
    .join("")
    .toUpperCase();
}

export const DocumentsRepo = {
  async insert(input: {
    originalFilename: string;
    mimeType: string;
    bytes: Buffer;
  }): Promise<string> {
    const id = uuidHex();
    await withConnection(async (conn) => {
      await conn.execute(
        `INSERT INTO documents (id, original_filename, mime_type, byte_size, file_blob)
         VALUES (HEXTORAW(:id), :filename, :mimeType, :byteSize, :blob)`,
        {
          id,
          filename: input.originalFilename,
          mimeType: input.mimeType,
          byteSize: input.bytes.length,
          blob: input.bytes,
        }
      );
    });
    return id;
  },

  async findById(id: string): Promise<DocumentRow | null> {
    return withConnection(async (conn) => {
      const result = await conn.execute<Record<string, unknown>>(
        `SELECT id, doc_type, status, original_filename, mime_type, byte_size,
                page_count, language, failed_reason, created_at, updated_at,
                extracted_text, summary
         FROM documents
         WHERE id = HEXTORAW(:id)`,
        { id },
        { outFormat: oracledb.OUT_FORMAT_OBJECT }
      );
      const row = result.rows?.[0];
      return row ? documentRowSchema.parse(row) : null;
    });
  },

  async list(filters: {
    docType?: DocType;
    status?: DocStatus;
    limit?: number;
    offset?: number;
  }): Promise<DocumentListItem[]> {
    const limit = filters.limit ?? 25;
    const offset = filters.offset ?? 0;
    return withConnection(async (conn) => {
      const result = await conn.execute<Record<string, unknown>>(
        `SELECT id, doc_type, status, original_filename, byte_size, created_at
         FROM documents
         WHERE (:docType IS NULL OR doc_type = :docType)
           AND (:statusFilter IS NULL OR status = :statusFilter)
         ORDER BY created_at DESC
         OFFSET :offset ROWS FETCH NEXT :lim ROWS ONLY`,
        {
          docType: filters.docType ?? null,
          statusFilter: filters.status ?? null,
          offset,
          lim: limit,
        },
        { outFormat: oracledb.OUT_FORMAT_OBJECT }
      );
      return (result.rows ?? []).map((row) => documentListItemRowSchema.parse(row));
    });
  },

  async updateStatus(id: string, status: DocStatus, failedReason?: string): Promise<void> {
    await withConnection(async (conn) => {
      await conn.execute(
        `UPDATE documents
         SET status = :status, failed_reason = :failedReason
         WHERE id = HEXTORAW(:id)`,
        { id, status, failedReason: failedReason ?? null }
      );
    });
  },

  async updateDocType(id: string, docType: DocType): Promise<void> {
    await withConnection(async (conn) => {
      await conn.execute(`UPDATE documents SET doc_type = :docType WHERE id = HEXTORAW(:id)`, {
        id,
        docType,
      });
    });
  },

  async extractText(id: string): Promise<string> {
    return withConnection(async (conn) => {
      await conn.execute(
        `UPDATE documents
         SET extracted_text = DBMS_VECTOR_CHAIN.UTL_TO_TEXT(file_blob)
         WHERE id = HEXTORAW(:id)`,
        { id }
      );
      const result = await conn.execute<Record<string, unknown>>(
        `SELECT extracted_text FROM documents WHERE id = HEXTORAW(:id)`,
        { id },
        { outFormat: oracledb.OUT_FORMAT_OBJECT }
      );
      const row = result.rows?.[0];
      return row ? (extractedTextRowSchema.parse(row).EXTRACTED_TEXT ?? "") : "";
    });
  },

  async generateSummary(id: string): Promise<string | null> {
    return withConnection(async (conn) => {
      const result = await conn.execute<Record<string, unknown>>(
        `SELECT DBMS_VECTOR_CHAIN.UTL_TO_SUMMARY(
                  extracted_text,
                  JSON('{"provider":"database","glevel":"sentence","numParagraphs":3}')
                ) AS SUMMARY
         FROM documents WHERE id = HEXTORAW(:id)`,
        { id },
        {
          outFormat: oracledb.OUT_FORMAT_OBJECT,
          fetchInfo: { SUMMARY: { type: oracledb.STRING } },
        }
      );
      const summary = (result.rows?.[0]?.SUMMARY as string | null) ?? null;
      await conn.execute(`UPDATE documents SET summary = :summary WHERE id = HEXTORAW(:id)`, {
        id,
        summary,
      });
      return summary;
    });
  },

  async setEmbedding(id: string): Promise<void> {
    // VECTOR_EMBEDDING embeds the whole extracted_text in one shot, which is only
    // valid because the sample documents are short, single-page files that fit the
    // model's token window (all_MiniLM_L12_v2 truncates past ~256 word pieces).
    // For larger documents, chunk first: UTL_TO_TEXT -> UTL_TO_CHUNKS -> UTL_TO_EMBEDDINGS.
    await withConnection(async (conn) => {
      await conn.execute(
        `UPDATE documents
         SET embedding = VECTOR_EMBEDDING(${EMBEDDING_MODEL_NAME} USING extracted_text AS data)
         WHERE id = HEXTORAW(:id)`,
        { id }
      );
    });
  },

  async streamBlob(id: string): Promise<{
    stream: Readable;
    mimeType: string;
    filename: string;
    byteSize: number;
  } | null> {
    return withConnection(async (c) => {
      const result = await c.execute<Record<string, unknown>>(
        `SELECT file_blob, mime_type, original_filename, byte_size
         FROM documents WHERE id = HEXTORAW(:id)`,
        { id },
        { outFormat: oracledb.OUT_FORMAT_OBJECT }
      );
      const raw = result.rows?.[0];
      if (!raw) return null;
      const row = blobRowSchema.parse(raw);
      const lob = row.FILE_BLOB as oracledb.Lob;
      const chunks: Buffer[] = [];
      await new Promise<void>((resolve, reject) => {
        lob.on("data", (chunk: Buffer) => chunks.push(chunk));
        lob.on("end", resolve);
        lob.on("error", reject);
      });
      return {
        stream: Readable.from(Buffer.concat(chunks)),
        mimeType: row.MIME_TYPE,
        filename: row.ORIGINAL_FILENAME,
        byteSize: row.BYTE_SIZE,
      };
    });
  },

  async classifyByVector(
    id: string,
    k = 5,
    unknownThreshold = 0.5
  ): Promise<{
    docType: DocType;
    confidence: number;
    neighbors: { docType: DocType; distance: number; filename: string }[];
  }> {
    return withConnection(async (conn) => {
      const result = await conn.execute<{
        DOC_TYPE: string;
        DISTANCE: number;
        ORIGINAL_FILENAME: string;
      }>(
        `SELECT b.doc_type AS DOC_TYPE,
                b.original_filename AS ORIGINAL_FILENAME,
                VECTOR_DISTANCE(a.embedding, b.embedding, COSINE) AS DISTANCE
         FROM documents a, documents b
         WHERE a.id = HEXTORAW(:id)
           AND b.id != HEXTORAW(:id)
           AND b.embedding IS NOT NULL
           AND b.doc_type IN ('invoice', 'purchase_order', 'delivery_note')
           AND b.status = 'done'
         ORDER BY DISTANCE
         FETCH FIRST :k ROWS ONLY`,
        { id, k },
        { outFormat: oracledb.OUT_FORMAT_OBJECT }
      );
      const neighbors = (result.rows ?? []).map((r) => ({
        docType: r.DOC_TYPE as DocType,
        distance: Number(r.DISTANCE),
        filename: r.ORIGINAL_FILENAME,
      }));
      if (neighbors.length === 0 || (neighbors[0] && neighbors[0].distance > unknownThreshold)) {
        return { docType: "unknown" as DocType, confidence: 0, neighbors };
      }
      const counts: Record<string, number> = {};
      for (const n of neighbors) counts[n.docType] = (counts[n.docType] ?? 0) + 1;
      const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
      const winner = sorted[0]![0] as DocType;
      const winnerCount = sorted[0]![1];
      const confidence = winnerCount / neighbors.length;
      return { docType: winner, confidence, neighbors };
    });
  },

  async findSimilar(id: string, k: number): Promise<SimilarDocument[]> {
    return withConnection(async (conn) => {
      const result = await conn.execute<Record<string, unknown>>(
        `SELECT documents.id, documents.doc_type, documents.original_filename,
                VECTOR_DISTANCE(documents.embedding, src.embedding, COSINE) AS distance
         FROM documents,
              (SELECT embedding FROM documents WHERE id = HEXTORAW(:id)) src
         WHERE documents.id != HEXTORAW(:id)
           AND documents.embedding IS NOT NULL
         ORDER BY distance
         FETCH FIRST :k ROWS ONLY`,
        { id, k },
        { outFormat: oracledb.OUT_FORMAT_OBJECT }
      );
      return (result.rows ?? []).map((row) => similarDocumentRowSchema.parse(row));
    });
  },
};
