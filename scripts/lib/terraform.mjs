#!/usr/bin/env zx
import { exitWithError } from "./utils.mjs";

export async function getOutputValues(terraformPath = "") {
  const tfOutputPathExists = await fs.pathExists(terraformPath);
  if (!tfOutputPathExists) exitWithError("Terraform path doesn't exist");

  const { stdout: stdoutPwd } = await $`pwd`;
  const currentPath = stdoutPwd.trim();
  await cd(path.normalize(terraformPath));

  const { stdout } = await $`terraform output -json`;
  const terraformOutput = JSON.parse(stdout);

  const values = {};
  for (const [key, content] of Object.entries(terraformOutput)) {
    values[key] = content.value;
  }

  await cd(currentPath);

  return values;
}
