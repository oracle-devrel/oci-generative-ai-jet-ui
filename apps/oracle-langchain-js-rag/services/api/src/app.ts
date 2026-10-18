import { existsSync } from "node:fs";
import { join } from "node:path";

import { serveStatic } from "@hono/node-server/serve-static";
import { cors } from "hono/cors";
import { Hono } from "hono";

import {
  askOracleRag,
  getDemoCorpus,
  getSetupState,
  inspectOracleDemoTable,
  resetDemoTable,
  seedDemoCorpus,
} from "@oracle-langchain-js-rag/core";
import { checkOracleConnection } from "@oracle-langchain-js-rag/db";
import type { AppStatus, AskRequest } from "@oracle-langchain-js-rag/shared";

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export function createApp(): Hono {
  const app = new Hono();

  app.use("/api/*", cors());

  app.get("/health", (c) =>
    c.json({
      ok: true,
      service: "oracle-langchain-js-rag-api",
    })
  );

  app.get("/api/status", async (c) => {
    const setup = getSetupState();
    let database: AppStatus["database"] = {
      connected: false,
      detail: setup.oracleConfigured
        ? "Oracle connection has not been checked yet"
        : `Missing: ${setup.missingOracleVars.join(", ")}`,
    };

    if (setup.oracleConfigured) {
      try {
        database = {
          connected: true,
          detail: await checkOracleConnection(),
        };
      } catch (error) {
        database = {
          connected: false,
          detail: errorMessage(error),
        };
      }
    }

    return c.json<AppStatus>({
      api: "ok",
      config: setup,
      database,
    });
  });

  app.get("/api/corpus", (c) => c.json(getDemoCorpus()));

  app.get("/api/inspect", async (c) => {
    try {
      return c.json(await inspectOracleDemoTable());
    } catch (error) {
      return c.json({ error: errorMessage(error) }, 500);
    }
  });

  app.post("/api/seed", async (c) => {
    try {
      return c.json(await seedDemoCorpus());
    } catch (error) {
      return c.json({ error: errorMessage(error) }, 500);
    }
  });

  app.post("/api/reset", async (c) => {
    try {
      return c.json(await resetDemoTable());
    } catch (error) {
      return c.json({ error: errorMessage(error) }, 500);
    }
  });

  app.post("/api/ask", async (c) => {
    try {
      const body = (await c.req.json().catch(() => ({}))) as Partial<AskRequest>;
      const question = body.question?.trim();
      if (!question) {
        return c.json({ error: "Question is required" }, 400);
      }

      return c.json(
        await askOracleRag(question, {
          k: body.k,
          category: body.category,
          retrievalMode: body.retrievalMode,
        })
      );
    } catch (error) {
      return c.json({ error: errorMessage(error) }, 500);
    }
  });

  const webDistDir = process.env.WEB_DIST_DIR;
  if (webDistDir && existsSync(webDistDir)) {
    app.use("/*", serveStatic({ root: webDistDir }));
    app.get("*", serveStatic({ path: join(webDistDir, "index.html") }));
  }

  return app;
}
