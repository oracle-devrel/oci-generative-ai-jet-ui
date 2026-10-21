import { serve } from "@hono/node-server";

import { createApp } from "./app.js";
import { loadProjectEnv } from "./env.js";

const envPath = loadProjectEnv();
const port = Number(process.env.PORT || 8787);

serve(
  {
    fetch: createApp().fetch,
    port,
  },
  (info) => {
    const envDetail = envPath ? ` using ${envPath}` : "";
    console.log(`Oracle LangChain.js RAG API listening on http://localhost:${info.port}${envDetail}`);
  }
);
