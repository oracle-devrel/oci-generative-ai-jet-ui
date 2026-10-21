import { existsSync, readdirSync, rmSync, statSync, unlinkSync } from "node:fs";
import { join } from "node:path";

const removeDeps = process.argv.includes("--deps");
const root = process.cwd();
const directoryNames = new Set(["dist", ".vite", "coverage"]);
if (removeDeps) directoryNames.add("node_modules");

const filePatterns = [/\.tsbuildinfo$/, /\.log$/];

function shouldSkipDirectory(name) {
  return (
    name === ".git" ||
    name === ".idea" ||
    name === ".vscode" ||
    (!removeDeps && name === "node_modules")
  );
}

function cleanDirectory(directory) {
  if (!existsSync(directory)) return;

  for (const entry of readdirSync(directory)) {
    if (shouldSkipDirectory(entry)) continue;

    const fullPath = join(directory, entry);
    const stats = statSync(fullPath);

    if (stats.isDirectory()) {
      if (directoryNames.has(entry)) {
        rmSync(fullPath, { recursive: true, force: true });
        console.log(`removed ${fullPath}`);
      } else {
        cleanDirectory(fullPath);
      }
      continue;
    }

    if (filePatterns.some((pattern) => pattern.test(entry))) {
      unlinkSync(fullPath);
      console.log(`removed ${fullPath}`);
    }
  }
}

cleanDirectory(root);
