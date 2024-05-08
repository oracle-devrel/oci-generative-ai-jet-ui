#!/usr/bin/env zx
import { exitWithError } from "./utils.mjs";

export async function bumpGradle(level = "patch") {
  const oldVersion = await getVersionGradle();
  let [major, minor, patch] = oldVersion.split(".").map((n) => parseInt(n));
  let newVersion;
  switch (level) {
    case "patch":
      newVersion = `${major}.${minor}.${patch + 1}`;
      break;
    case "minor":
      newVersion = `${major}.${minor + 1}.${0}`;
      break;
    case "major":
      newVersion = `${major + 1}.${0}.${0}`;
      break;
    default:
      console.log("No version bump");
      break;
  }
  try {
    const { exitCode, stderr } =
      await $`sed -I -e '/^version/s/${oldVersion}/${newVersion}/g' build.gradle`;
    if (exitCode !== 0) {
      exitWithError(stderr);
    }
    return newVersion;
  } catch (error) {
    exitWithError(error.stderr);
  }
}

export async function getVersionGradle() {
  try {
    const { stdout, exitCode, stderr } =
      await $`grep "version = " build.gradle`;
    if (exitCode !== 0) {
      exitWithError(stderr);
    }
    const version = stdout.trim().split("version = ")[1].replaceAll("'", "");
    return version;
  } catch (error) {
    exitWithError(error.stderr);
  }
}

export async function cleanGradle() {
  try {
    const { stdout, exitCode, stderr } = await $`./gradlew clean`;
    if (exitCode !== 0) {
      exitWithError(stderr);
    }
    console.log(stdout.trim());
  } catch (error) {
    exitWithError(error.stderr);
  }
}

export async function buildJarGradle() {
  try {
    const { stdout, exitCode, stderr } = await $`./gradlew bootJar`;
    if (exitCode !== 0) {
      exitWithError(stderr);
    }
    console.log(stdout.trim());
  } catch (error) {
    exitWithError(error.stderr);
  }
}
