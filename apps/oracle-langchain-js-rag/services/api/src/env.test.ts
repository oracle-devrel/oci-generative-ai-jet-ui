import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { afterEach, describe, expect, it } from "vitest";

import { loadProjectEnv } from "./env.js";

const envKey = "LC_JS_RAG_ENV_TEST_TOKEN";

describe("loadProjectEnv", () => {
  const tempRoots: string[] = [];

  afterEach(() => {
    delete process.env[envKey];
    for (const root of tempRoots.splice(0)) {
      rmSync(root, { force: true, recursive: true });
    }
  });

  it("loads the root .env when the API runs from services/api", () => {
    const projectRoot = mkdtempSync(join(tmpdir(), "lc-js-rag-"));
    tempRoots.push(projectRoot);

    const apiCwd = join(projectRoot, "services", "api");
    mkdirSync(apiCwd, { recursive: true });
    writeFileSync(join(projectRoot, ".env"), `${envKey}=from-root\n`, "utf8");

    const loadedPath = loadProjectEnv(apiCwd);

    expect(loadedPath).toBe(join(projectRoot, ".env"));
    expect(process.env[envKey]).toBe("from-root");
  });
});
