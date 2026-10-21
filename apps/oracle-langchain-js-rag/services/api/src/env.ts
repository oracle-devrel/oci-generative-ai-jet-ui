import { existsSync } from "node:fs";
import { resolve } from "node:path";

import { config as loadDotenv } from "dotenv";

export function findProjectEnv(cwd = process.cwd()): string | undefined {
  const candidates = [
    resolve(cwd, ".env"),
    resolve(cwd, "..", ".env"),
    resolve(cwd, "..", "..", ".env"),
    resolve(cwd, "..", "..", "..", ".env"),
  ];

  return candidates.find((candidate) => existsSync(candidate));
}

export function loadProjectEnv(cwd = process.cwd()): string | undefined {
  const envPath = findProjectEnv(cwd);

  if (envPath) {
    loadDotenv({ override: false, path: envPath });
    return envPath;
  }

  loadDotenv({ override: false });
  return undefined;
}
