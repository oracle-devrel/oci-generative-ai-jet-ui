import { z } from "zod";
import { commonEnvelope } from "./common.js";

export const invoiceLineItem = z.object({
  description: z.string(),
  quantity: z.number(),
  unitPrice: z.number(),
  total: z.number(),
});

export const invoiceFields = z.object({
  envelope: commonEnvelope,
  vendor: z.string(),
  invoiceNumber: z.string(),
  invoiceDate: z.string(),
  dueDate: z.string().nullable(),
  currency: z.string().length(3),
  subtotal: z.number(),
  tax: z.number(),
  total: z.number(),
  lineItems: z.array(invoiceLineItem),
});

export type InvoiceFields = z.infer<typeof invoiceFields>;
export type InvoiceLineItem = z.infer<typeof invoiceLineItem>;
