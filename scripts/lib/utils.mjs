#!/usr/bin/env zx

export async function readEnvJson() {
  const envFilePath = ".env.json";
  const envFileExists = await fs.pathExists(envFilePath);
  if (envFileExists) {
    return fs.readJson(envFilePath);
  }
  return writeEnvJson({});
}

export async function writeEnvJson(properties) {
  const envFilePath = ".env.json";
  await fs.writeJson(envFilePath, properties, { spaces: 2 });
  return properties;
}

export async function validateBumpLevel(level) {
  if (!["major", "minor", "patch"].includes(level)) {
    exitWithError("Error: release version must be 'major', 'minor' or 'patch'");
  }
  return level;
}

export async function printRegionNames(regions) {
  console.log("printRegionNames");
  const regionsByZone = regions.reduce((acc, cur) => {
    const zone = cur.name.split("-")[0];
    if (acc[zone]) {
      acc[zone].push(cur.name);
    } else {
      acc[zone] = [cur.name];
    }
    return acc;
  }, {});
  Object.keys(regionsByZone).forEach((zone) =>
    console.log(`\t${chalk.yellow(zone)}: ${regionsByZone[zone].join(", ")}`)
  );
}

export async function getRegionByKey(code = "fra") {
  const output = (await $`oci iam region list`).stdout.trim();
  const { data } = JSON.parse(output);
  return data.find((r) => code.toUpperCase() === r.key);
}

export async function setVariableFromEnvOrPrompt(
  envKey,
  questionText,
  printChoices
) {
  const envValue = process.env[envKey];
  if (envValue) {
    return envValue;
  } else {
    if (printChoices) {
      printChoices();
    }
    const answer = await question(`${questionText}: `);
    return answer;
  }
}

export async function exitWithError(errorMessage = "") {
  console.error(chalk.red(errorMessage.trim()));
  process.exit(1);
}

export async function checkRequiredProgramsExist(programs) {
  try {
    for (let program of programs) {
      await which(program);
      console.log(`${chalk.green("[ok]")} ${program}`);
    }
  } catch (error) {
    exitWithError(`Error: Required command ${error.message}`);
  }
}
