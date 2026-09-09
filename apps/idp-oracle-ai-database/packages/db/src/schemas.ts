import { z } from "zod";
import { DOC_TYPES, DOC_STATUSES } from "@idp/shared";

const idFromBuffer = z.instanceof(Buffer).transform((b) => b.toString("hex").toUpperCase());

const isoFromDate = z.instanceof(Date).transform((d) => d.toISOString());

export const documentRowSchema = z
  .object({
    ID: idFromBuffer,
    DOC_TYPE: z.enum(DOC_TYPES),
    STATUS: z.enum(DOC_STATUSES),
    ORIGINAL_FILENAME: z.string(),
    MIME_TYPE: z.string(),
    BYTE_SIZE: z.number(),
    PAGE_COUNT: z.number().nullable(),
    LANGUAGE: z.string().nullable(),
    FAILED_REASON: z.string().nullable(),
    CREATED_AT: isoFromDate,
    UPDATED_AT: isoFromDate,
    EXTRACTED_TEXT: z.string().nullable(),
    SUMMARY: z.string().nullable(),
  })
  .transform((row) => ({
    id: row.ID,
    docType: row.DOC_TYPE,
    status: row.STATUS,
    originalFilename: row.ORIGINAL_FILENAME,
    mimeType: row.MIME_TYPE,
    byteSize: row.BYTE_SIZE,
    pageCount: row.PAGE_COUNT,
    language: row.LANGUAGE,
    failedReason: row.FAILED_REASON,
    createdAt: row.CREATED_AT,
    updatedAt: row.UPDATED_AT,
    extractedText: row.EXTRACTED_TEXT,
    summary: row.SUMMARY,
  }));

export type DocumentRow = z.infer<typeof documentRowSchema>;

export const documentListItemRowSchema = z
  .object({
    ID: idFromBuffer,
    DOC_TYPE: z.enum(DOC_TYPES),
    STATUS: z.enum(DOC_STATUSES),
    ORIGINAL_FILENAME: z.string(),
    BYTE_SIZE: z.number(),
    CREATED_AT: isoFromDate,
  })
  .transform((row) => ({
    id: row.ID,
    docType: row.DOC_TYPE,
    status: row.STATUS,
    originalFilename: row.ORIGINAL_FILENAME,
    byteSize: row.BYTE_SIZE,
    createdAt: row.CREATED_AT,
  }));

export type DocumentListItem = z.infer<typeof documentListItemRowSchema>;

export const similarDocumentRowSchema = z
  .object({
    ID: idFromBuffer,
    DOC_TYPE: z.enum(DOC_TYPES),
    ORIGINAL_FILENAME: z.string(),
    DISTANCE: z.number(),
  })
  .transform((row) => ({
    id: row.ID,
    docType: row.DOC_TYPE,
    originalFilename: row.ORIGINAL_FILENAME,
    distance: row.DISTANCE,
  }));

export type SimilarDocument = z.infer<typeof similarDocumentRowSchema>;

export const blobRowSchema = z.object({
  FILE_BLOB: z.unknown(),
  MIME_TYPE: z.string(),
  ORIGINAL_FILENAME: z.string(),
  BYTE_SIZE: z.number(),
});

export const fieldsPayloadRowSchema = z
  .object({
    PAYLOAD: z.string(),
  })
  .transform((row) => JSON.parse(row.PAYLOAD) as Record<string, unknown>);

export type FieldsPayload = z.infer<typeof fieldsPayloadRowSchema>;

export const extractedTextRowSchema = z.object({
  EXTRACTED_TEXT: z.string().nullable(),
});
