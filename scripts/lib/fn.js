#!/usr/bin/env zx
import { exitWithError } from "./utils.mjs";

export async function createFnOracleContext(contextName) {
  console.log(
    chalk.yellow(`fn create context ${contextName} --provider oracle`)
  );
  try {
    const { stdout, exitCode, stderr } =
      await $`fn create context ${contextName} --provider oracle`;
    if (exitCode !== 0) {
      exitWithError(stderr);
    }
    console.log(chalk.green(`Context ${contextName} created`));
    return stdout.trim();
  } catch (error) {
    exitWithError(error.stderr);
  }
}

export async function listFnOracleContext() {
  try {
    const { stdout, exitCode, stderr } = await $`fn list context -output json`;
    if (exitCode !== 0) {
      exitWithError(stderr);
    }
    return JSON.parse(stdout.trim());
  } catch (error) {
    exitWithError(error.stderr);
  }
}

export async function useFnContext(contextName) {
  const contexts = await listFnOracleContext();
  const currentContext = contexts.find((c) => c.current);
  if (currentContext.name === contextName) {
    console.log(chalk.green(`Context ${contextName} already in use.`));
    return;
  }
  console.log(chalk.yellow(`fn use context ${contextName}`));
  try {
    const { stdout, exitCode, stderr } = await $`fn use context ${contextName}`;
    if (exitCode !== 0) {
      exitWithError(stderr);
    }
    console.log(chalk.green(`Context ${contextName} in use.`));
    return stdout.trim();
  } catch (error) {
    exitWithError(error.stderr);
  }
}

export async function setFnProfileName(profileName = "DEFAULT") {
  console.log(chalk.yellow(`fn update context oracle.profile ${profileName}`));
  try {
    const { stdout, exitCode, stderr } =
      await $`fn update context oracle.profile ${profileName}`;
    if (exitCode !== 0) {
      exitWithError(stderr);
    }
    console.log(chalk.green(`Profile ${profileName} set.`));
    return stdout.trim();
  } catch (error) {
    exitWithError(error.stderr);
  }
}

export async function setFnCompartment(compartmentId) {
  if (!compartmentId) {
    exitWithError("Compartment OCID required");
  }
  console.log(
    chalk.yellow(`fn update context oracle.compartment-id ${compartmentId}`)
  );
  try {
    const { stdout, exitCode, stderr } =
      await $`fn update context oracle.compartment-id ${compartmentId}`;
    if (exitCode !== 0) {
      exitWithError(stderr);
    }
    console.log(chalk.green(`Compartment ${compartmentId} set.`));
    return stdout.trim();
  } catch (error) {
    exitWithError(error.stderr);
  }
}

export async function setFnApiUrl(regionKey) {
  if (!regionKey) {
    exitWithError("Region key required");
  }
  console.log(
    chalk.yellow(
      `fn update context api-url https://functions.${regionKey}.oci.oraclecloud.com`
    )
  );
  try {
    const { stdout, exitCode, stderr } =
      await $`fn update context api-url https://functions.${regionKey}.oci.oraclecloud.com`;
    if (exitCode !== 0) {
      exitWithError(stderr);
    }
    console.log(
      chalk.green(
        `API URL https://functions.${regionKey}.oci.oraclecloud.com set.`
      )
    );
    return stdout.trim();
  } catch (error) {
    exitWithError(error.stderr);
  }
}

export async function setFnRegistry(regionKey, namespace, repoNamePrefix) {
  if (!regionKey) {
    exitWithError("Region key required");
  }
  if (!namespace) {
    exitWithError("Namespace required");
  }
  if (!repoNamePrefix) {
    exitWithError("Repo name Prefix required");
  }
  console.log(
    chalk.yellow(
      `fn update context registry ${regionKey}.ocir.io/${namespace}/${repoNamePrefix}`
    )
  );
  try {
    const { stdout, exitCode, stderr } =
      await $`fn update context registry ${regionKey}.ocir.io/${namespace}/${repoNamePrefix}`;
    if (exitCode !== 0) {
      exitWithError(stderr);
    }
    console.log(
      chalk.green(
        `Registry ${regionKey}.ocir.io/${namespace}/${repoNamePrefix} set.`
      )
    );
    return stdout.trim();
  } catch (error) {
    exitWithError(error.stderr);
  }
}

export async function setFnRegistryCompartment(compartmentId) {
  if (!compartmentId) {
    exitWithError("Compartment OCID required");
  }
  console.log(
    chalk.yellow(
      `fn update context oracle.image-compartment-id ${compartmentId}`
    )
  );
  try {
    const { stdout, exitCode, stderr } =
      await $`fn update context oracle.image-compartment-id ${compartmentId}`;
    if (exitCode !== 0) {
      exitWithError(stderr);
    }
    console.log(chalk.green(`Registry compartment ${compartmentId} set.`));
    return stdout.trim();
  } catch (error) {
    exitWithError(error.stderr);
  }
}
