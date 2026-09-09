import { Hono } from "hono";
import { cors } from "hono/cors";
import { documents, initConfig } from "@idp/core";
import { logger } from "@idp/logger";
import { requestLogger, jsonError } from "./middleware.js";
import {
  MAX_UPLOAD_BYTES,
  type DocType,
  type DocStatus,
  DOC_TYPES,
  DOC_STATUSES,
} from "@idp/shared";

export function createApp() {
  const app = new Hono();

  app.use("*", cors());
  app.use("*", requestLogger());

  app.use("*", async (c, next) => {
    await initConfig();
    await next();
  });

  app.get("/health", (c) => c.json({ ok: true }));

  app.post("/documents", async (c) => {
    const form = await c.req.parseBody();
    const file = form.file;
    if (!(file instanceof File)) {
      return jsonError(c, 400, "missing_file", 'multipart field "file" is required');
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      return jsonError(c, 413, "file_too_large", `File exceeds ${MAX_UPLOAD_BYTES} bytes`);
    }
    const bytes = Buffer.from(await file.arrayBuffer());
    const summary = await documents.uploadAndIngest({
      originalFilename: file.name,
      mimeType: file.type || "application/pdf",
      bytes,
    });
    return c.json(summary, 201);
  });

  app.get("/documents", async (c) => {
    const docTypeParam = c.req.query("docType");
    const statusParam = c.req.query("status");
    if (docTypeParam && !DOC_TYPES.includes(docTypeParam as DocType)) {
      return jsonError(c, 400, "invalid_doc_type", `unknown docType: ${docTypeParam}`);
    }
    if (statusParam && !DOC_STATUSES.includes(statusParam as DocStatus)) {
      return jsonError(c, 400, "invalid_status", `unknown status: ${statusParam}`);
    }
    const result = await documents.list({
      docType: docTypeParam as DocType | undefined,
      status: statusParam as DocStatus | undefined,
      limit: c.req.query("limit") ? Number(c.req.query("limit")) : undefined,
      offset: c.req.query("offset") ? Number(c.req.query("offset")) : undefined,
    });
    return c.json(result);
  });

  app.get("/documents/:id", async (c) => {
    const summary = await documents.get(c.req.param("id"));
    if (!summary) return jsonError(c, 404, "not_found", "document not found");
    return c.json(summary);
  });

  app.get("/documents/:id/file", async (c) => {
    const file = await documents.getFile(c.req.param("id"));
    if (!file) return jsonError(c, 404, "not_found", "document not found");
    c.header("Content-Type", file.mimeType);
    c.header("Content-Disposition", `inline; filename="${file.filename}"`);
    c.header("Content-Length", String(file.byteSize));
    const chunks: Buffer[] = [];
    for await (const chunk of file.stream) {
      chunks.push(chunk as Buffer);
    }
    return c.body(Buffer.concat(chunks));
  });

  app.get("/documents/:id/similar", async (c) => {
    const k = c.req.query("k") ? Number(c.req.query("k")) : 5;
    const items = await documents.findSimilar(c.req.param("id"), k);
    return c.json({ items });
  });

  app.onError((err, c) => {
    logger.error("unhandled error", { error: err.message, stack: err.stack });
    return jsonError(c, 500, "internal_error", "an internal error occurred");
  });

  return app;
}
