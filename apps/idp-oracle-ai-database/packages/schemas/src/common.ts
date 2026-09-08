import { z } from "zod";

export const commonEnvelope = z.object({
  docType: z.enum(["invoice", "purchase_order", "delivery_note", "unknown"]),
  summary: z.string().min(1).max(500),
  language: z.string().length(2),
  pageCount: z.number().int().positive().nullable(),
  confidence: z.number().min(0).max(1).nullable(),
});

export type CommonEnvelope = z.infer<typeof commonEnvelope>;

export const classificationResult = z.object({
  docType: z.enum(["invoice", "purchase_order", "delivery_note", "unknown"]),
  confidence: z.number().min(0).max(1).nullable(),
});

export type ClassificationResult = z.infer<typeof classificationResult>;
