import { Readable } from "node:stream";
import {
  DocumentsRepo,
  FieldsRepo,
  type DocumentRow,
  type DocumentListItem,
  type SimilarDocument,
} from "@idp/db";
import type { DocType, DocStatus } from "@idp/shared";
import { logger } from "@idp/logger";
import { ingestDocument } from "./ingest.js";

export type DocumentSummary = Omit<DocumentRow, "extractedText"> & {
  fields: object | null;
};

export interface DocumentFile {
  stream: Readable;
  mimeType: string;
  filename: string;
  byteSize: number;
}

export interface ListFilters {
  docType?: DocType;
  status?: DocStatus;
  limit?: number;
  offset?: number;
}

export interface ListResult {
  items: DocumentListItem[];
  limit: number;
  offset: number;
}

async function fieldsForDoc(doc: DocumentRow): Promise<object | null> {
  switch (doc.docType) {
    case "invoice":
      return FieldsRepo.getInvoice(doc.id);
    case "purchase_order":
      return FieldsRepo.getPurchaseOrder(doc.id);
    case "delivery_note":
      return FieldsRepo.getDeliveryNote(doc.id);
    default:
      return null;
  }
}

function toSummary(doc: DocumentRow, fields: object | null): DocumentSummary {
  const { extractedText: _omit, ...rest } = doc;
  return { ...rest, fields };
}

export const documents = {
  async list(filters: ListFilters): Promise<ListResult> {
    const limit = Math.min(filters.limit ?? 25, 100);
    const offset = filters.offset ?? 0;
    const items = await DocumentsRepo.list({
      docType: filters.docType,
      status: filters.status,
      limit,
      offset,
    });
    return { items, limit, offset };
  },

  async get(id: string): Promise<DocumentSummary | null> {
    const doc = await DocumentsRepo.findById(id);
    if (!doc) return null;
    const fields = await fieldsForDoc(doc);
    return toSummary(doc, fields);
  },

  async getFile(id: string): Promise<DocumentFile | null> {
    return DocumentsRepo.streamBlob(id);
  },

  async findSimilar(id: string, k: number): Promise<SimilarDocument[]> {
    const bounded = Math.min(Math.max(k, 1), 20);
    return DocumentsRepo.findSimilar(id, bounded);
  },

  async uploadAndIngest(input: {
    originalFilename: string;
    mimeType: string;
    bytes: Buffer;
  }): Promise<DocumentSummary> {
    const id = await DocumentsRepo.insert(input);
    logger.info("document received", {
      id,
      filename: input.originalFilename,
      bytes: input.bytes.length,
    });
    await ingestDocument(id);
    const summary = await this.get(id);
    if (!summary) throw new Error(`document ${id} disappeared after ingest`);
    return summary;
  },
};
