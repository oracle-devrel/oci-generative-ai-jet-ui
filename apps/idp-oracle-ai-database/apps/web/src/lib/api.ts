import type { DocType, DocStatus, DocumentEnvelope } from "@idp/shared";
import type { InvoiceFields, PurchaseOrderFields, DeliveryNoteFields } from "@idp/schemas";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

export interface DocumentListItem {
  id: string;
  docType: DocType;
  status: DocStatus;
  originalFilename: string;
  byteSize: number;
  createdAt: string;
}

export interface DocumentDetail extends DocumentEnvelope {
  fields:
    | (InvoiceFields & { _id: string })
    | (PurchaseOrderFields & { _id: string })
    | (DeliveryNoteFields & { _id: string })
    | null;
}

export interface SimilarItem {
  id: string;
  docType: DocType;
  originalFilename: string;
  distance: number;
}

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  uploadDocument(file: File): Promise<DocumentDetail> {
    const fd = new FormData();
    fd.append("file", file);
    return jsonFetch<DocumentDetail>("/documents", { method: "POST", body: fd });
  },
  listDocuments(filters: {
    docType?: DocType;
    status?: DocStatus;
    limit?: number;
    offset?: number;
  }): Promise<{ items: DocumentListItem[]; limit: number; offset: number }> {
    const qs = new URLSearchParams();
    if (filters.docType) qs.set("docType", filters.docType);
    if (filters.status) qs.set("status", filters.status);
    if (filters.limit) qs.set("limit", String(filters.limit));
    if (filters.offset) qs.set("offset", String(filters.offset));
    return jsonFetch(`/documents?${qs.toString()}`);
  },
  getDocument(id: string): Promise<DocumentDetail> {
    return jsonFetch(`/documents/${id}`);
  },
  similarDocuments(id: string, k = 5): Promise<{ items: SimilarItem[] }> {
    return jsonFetch(`/documents/${id}/similar?k=${k}`);
  },
  fileUrl(id: string): string {
    return `${BASE}/documents/${id}/file`;
  },
};
