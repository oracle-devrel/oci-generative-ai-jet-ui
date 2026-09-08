import type { Context } from "hono";
import { logger } from "@idp/logger";

export function jsonError(c: Context, status: number, code: string, message: string) {
  return c.json({ code, message }, status as 400);
}

export function requestLogger() {
  return async (c: Context, next: () => Promise<void>) => {
    const start = Date.now();
    await next();
    logger.info("request", {
      method: c.req.method,
      path: c.req.path,
      status: c.res.status,
      durationMs: Date.now() - start,
    });
  };
}
