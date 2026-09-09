import { config as loadEnv } from "dotenv";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

loadEnv({
  path: join(dirname(fileURLToPath(import.meta.url)), "..", "..", "..", "..", ".env"),
});

const { serve } = await import("@hono/node-server");
const { createApp } = await import("./app.js");

const port = Number(process.env.PORT ?? 8787);
const app = createApp();

serve({ fetch: app.fetch, port }, (info) => {
  console.log(`api listening on http://localhost:${info.port}`);
});
