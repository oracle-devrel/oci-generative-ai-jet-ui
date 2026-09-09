import type { DocType } from "@idp/shared";
import { zodToJsonSchema } from "zod-to-json-schema";
import { z } from "zod";
import { invoiceFields } from "./invoice.js";
import { purchaseOrderFields } from "./purchase-order.js";
import { deliveryNoteFields } from "./delivery-note.js";

export const fieldsSchemaByType = {
  invoice: invoiceFields,
  purchase_order: purchaseOrderFields,
  delivery_note: deliveryNoteFields,
} as const;

export type ExtractableDocType = keyof typeof fieldsSchemaByType;

export type FieldsByType = {
  invoice: z.infer<typeof invoiceFields>;
  purchase_order: z.infer<typeof purchaseOrderFields>;
  delivery_note: z.infer<typeof deliveryNoteFields>;
};

export function getFieldsSchema<T extends ExtractableDocType>(
  docType: T
): (typeof fieldsSchemaByType)[T] {
  return fieldsSchemaByType[docType];
}

export function getJsonSchemaForType(docType: ExtractableDocType): object {
  return zodToJsonSchema(fieldsSchemaByType[docType], {
    target: "jsonSchema7",
    $refStrategy: "none",
  });
}

export function isExtractable(docType: DocType): docType is ExtractableDocType {
  return docType === "invoice" || docType === "purchase_order" || docType === "delivery_note";
}
