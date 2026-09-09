import oracledb from "oracledb";
import { withConnection } from "../pool.js";
import { fieldsPayloadRowSchema, type FieldsPayload } from "../schemas.js";
import type { InvoiceFields, PurchaseOrderFields, DeliveryNoteFields } from "@idp/schemas";

async function upsertFields(documentId: string, payload: object): Promise<void> {
  await withConnection(async (conn) => {
    await conn.execute(
      `MERGE INTO document_fields f
       USING (SELECT HEXTORAW(:id) AS doc_id FROM dual) src
       ON (f.document_id = src.doc_id)
       WHEN MATCHED THEN UPDATE SET payload = :payload
       WHEN NOT MATCHED THEN INSERT (document_id, payload)
         VALUES (src.doc_id, :payload)`,
      { id: documentId, payload: JSON.stringify(payload) }
    );
  });
}

async function fetchFieldsForDoc(documentId: string): Promise<FieldsPayload | null> {
  return withConnection(async (conn) => {
    const result = await conn.execute<Record<string, unknown>>(
      `SELECT JSON_SERIALIZE(payload RETURNING CLOB) AS PAYLOAD
       FROM document_fields
       WHERE document_id = HEXTORAW(:id)`,
      { id: documentId },
      {
        outFormat: oracledb.OUT_FORMAT_OBJECT,
        fetchInfo: { PAYLOAD: { type: oracledb.STRING } },
      }
    );
    const row = result.rows?.[0];
    if (!row || row.PAYLOAD == null) return null;
    return fieldsPayloadRowSchema.parse(row);
  });
}

export const FieldsRepo = {
  upsertInvoice(id: string, fields: InvoiceFields): Promise<void> {
    return upsertFields(id, fields);
  },
  upsertPurchaseOrder(id: string, fields: PurchaseOrderFields): Promise<void> {
    return upsertFields(id, fields);
  },
  upsertDeliveryNote(id: string, fields: DeliveryNoteFields): Promise<void> {
    return upsertFields(id, fields);
  },

  getInvoice(id: string): Promise<FieldsPayload | null> {
    return fetchFieldsForDoc(id);
  },
  getPurchaseOrder(id: string): Promise<FieldsPayload | null> {
    return fetchFieldsForDoc(id);
  },
  getDeliveryNote(id: string): Promise<FieldsPayload | null> {
    return fetchFieldsForDoc(id);
  },
};
