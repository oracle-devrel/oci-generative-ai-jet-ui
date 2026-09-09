import { z } from "zod";
import { commonEnvelope } from "./common.js";

export const deliveryNoteLineItem = z.object({
  description: z.string(),
  quantity: z.number(),
  unit: z.string(),
});

export const deliveryNoteFields = z.object({
  envelope: commonEnvelope,
  deliveryNoteNumber: z.string(),
  poReference: z.string().nullable(),
  supplier: z.string(),
  recipient: z.string(),
  deliveryDate: z.string(),
  shipTo: z.string(),
  carrier: z.string().nullable(),
  lineItems: z.array(deliveryNoteLineItem),
});

export type DeliveryNoteFields = z.infer<typeof deliveryNoteFields>;
export type DeliveryNoteLineItem = z.infer<typeof deliveryNoteLineItem>;
