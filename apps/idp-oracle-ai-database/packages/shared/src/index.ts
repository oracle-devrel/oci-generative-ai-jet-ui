export const DOC_TYPES = ["invoice", "purchase_order", "delivery_note", "unknown"] as const;
export type DocType = (typeof DOC_TYPES)[number];

export const DOC_TYPE_LABELS: Record<DocType, string> = {
  invoice: "Invoice",
  purchase_order: "Purchase order",
  delivery_note: "Delivery note",
  unknown: "Unknown",
};

export const DOC_STATUSES = [
  "pending",
  "text_extracted",
  "classified",
  "fields_extracted",
  "embedded",
  "done",
  "failed",
] as const;
export type DocStatus = (typeof DOC_STATUSES)[number];

export const EMBEDDING_DIMENSIONS = 384;
export const EMBEDDING_MODEL_NAME = "doc_embedder";

export const MAX_UPLOAD_BYTES = 6 * 1024 * 1024;

export interface DocumentEnvelope {
  id: string;
  docType: DocType;
  status: DocStatus;
  originalFilename: string;
  mimeType: string;
  byteSize: number;
  pageCount: number | null;
  language: string | null;
  failedReason: string | null;
  createdAt: string;
  updatedAt: string;
  summary: string | null;
}
