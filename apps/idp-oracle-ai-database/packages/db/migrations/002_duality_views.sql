-- Run as the `idp` user.
-- One JSON Duality View per document type. Each view exposes a typed JSON
-- shape that the API reads and writes as a single object, while the
-- underlying rows in `documents` and `document_fields` stay relational.

CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW invoice_dv AS
SELECT JSON {
  '_id'              : d.id,
  'docType'          : d.doc_type,
  'status'           : d.status,
  'originalFilename' : d.original_filename,
  'mimeType'         : d.mime_type,
  'byteSize'         : d.byte_size,
  'pageCount'        : d.page_count,
  'language'         : d.language,
  'failedReason'     : d.failed_reason,
  'createdAt'        : d.created_at,
  'updatedAt'        : d.updated_at,
  'fields'           : (
    SELECT f.payload
    FROM document_fields f WITH UPDATE
    WHERE f.document_id = d.id
  )
}
FROM documents d WITH UPDATE
WHERE d.doc_type = 'invoice' WITH CHECK OPTION;

CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW purchase_order_dv AS
SELECT JSON {
  '_id'              : d.id,
  'docType'          : d.doc_type,
  'status'           : d.status,
  'originalFilename' : d.original_filename,
  'mimeType'         : d.mime_type,
  'byteSize'         : d.byte_size,
  'pageCount'        : d.page_count,
  'language'         : d.language,
  'failedReason'     : d.failed_reason,
  'createdAt'        : d.created_at,
  'updatedAt'        : d.updated_at,
  'fields'           : (
    SELECT f.payload
    FROM document_fields f WITH UPDATE
    WHERE f.document_id = d.id
  )
}
FROM documents d WITH UPDATE
WHERE d.doc_type = 'purchase_order' WITH CHECK OPTION;

CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW delivery_note_dv AS
SELECT JSON {
  '_id'              : d.id,
  'docType'          : d.doc_type,
  'status'           : d.status,
  'originalFilename' : d.original_filename,
  'mimeType'         : d.mime_type,
  'byteSize'         : d.byte_size,
  'pageCount'        : d.page_count,
  'language'         : d.language,
  'failedReason'     : d.failed_reason,
  'createdAt'        : d.created_at,
  'updatedAt'        : d.updated_at,
  'fields'           : (
    SELECT f.payload
    FROM document_fields f WITH UPDATE
    WHERE f.document_id = d.id
  )
}
FROM documents d WITH UPDATE
WHERE d.doc_type = 'delivery_note' WITH CHECK OPTION;

CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW document_dv AS
SELECT JSON {
  '_id'              : d.id,
  'docType'          : d.doc_type,
  'status'           : d.status,
  'originalFilename' : d.original_filename,
  'mimeType'         : d.mime_type,
  'byteSize'         : d.byte_size,
  'pageCount'        : d.page_count,
  'language'         : d.language,
  'failedReason'     : d.failed_reason,
  'createdAt'        : d.created_at,
  'updatedAt'        : d.updated_at
}
FROM documents d;
