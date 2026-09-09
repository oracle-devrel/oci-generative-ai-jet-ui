import { z } from "zod";
import { commonEnvelope } from "./common.js";

export const purchaseOrderLineItem = z.object({
  description: z.string(),
  quantity: z.number(),
  unitPrice: z.number(),
  total: z.number(),
});

export const purchaseOrderFields = z.object({
  envelope: commonEnvelope,
  poNumber: z.string(),
  buyer: z.string(),
  supplier: z.string(),
  orderDate: z.string(),
  expectedDeliveryDate: z.string().nullable(),
  shipTo: z.string().nullable(),
  currency: z.string().length(3),
  subtotal: z.number(),
  tax: z.number(),
  total: z.number(),
  lineItems: z.array(purchaseOrderLineItem),
});

export type PurchaseOrderFields = z.infer<typeof purchaseOrderFields>;
export type PurchaseOrderLineItem = z.infer<typeof purchaseOrderLineItem>;
