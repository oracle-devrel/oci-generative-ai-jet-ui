#!/usr/bin/env zx
import { exitWithError } from "./utils.mjs";
import { where, max } from "underscore";

export async function getRegions(profile = "DEFAULT", tenancyId) {
  try {
    const output = (
      await $`oci iam region-subscription list \
              --tenancy-id ${tenancyId} \
              --profile ${profile}`
    ).stdout.trim();
    const { data } = JSON.parse(output);
    return data
      .filter((r) => r.status === "READY")
      .map((r) => ({
        key: r["region-key"].toLowerCase(),
        name: r["region-name"],
        isHomeRegion: r["is-home-region"],
      }));
  } catch (error) {
    exitWithError(`Error: get regions ${error.message}`);
  }
}

export async function getNamespace(profile) {
  const output = (await $`oci os ns get --profile ${profile}`).stdout.trim();
  const { data } = JSON.parse(output);
  return data;
}

export async function listAdbDatabases(compartmentId) {
  try {
    const { stdout, exitCode, stderr } =
      await $`oci db autonomous-database list --all --compartment-id ${compartmentId}`;
    if (exitCode !== 0) {
      exitWithError(stderr);
    }
    if (!stdout.length) return [];
    return JSON.parse(stdout.trim()).data;
  } catch (error) {
    exitWithError(`Error: download wallet ${error.stderr}`);
  }
}

export async function downloadAdbWallet(adbId, walletFilePath, walletPassword) {
  try {
    const { exitCode, stderr } =
      await $`oci db autonomous-database generate-wallet \
      --autonomous-database-id ${adbId} \
      --file ${walletFilePath} \
      --password ${walletPassword}`;
    if (exitCode !== 0) {
      exitWithError(stderr);
    }
    console.log(`Wallet downloaded on ${chalk.green(walletFilePath)}`);
  } catch (error) {
    exitWithError(`Error: download wallet ${error.stderr}`);
  }
}

export async function getAvailableShapes(options = {}) {
  try {
    const output = (
      await $`oci compute shape list --compartment-id ${await getTenancyId()}`
    ).stdout.trim();
    const { data } = JSON.parse(output);
    const { type = "*", flex, includeOld = false } = options;
    return data
      .filter((shape) => {
        if (shape.shape.includes("Standard1.")) return false;
        return true;
      })
      .filter((shape) => {
        if (type === "*") return true;
        if (type === "bm") return shape.shape.startsWith("BM.");
        if (type === "vm") return shape.shape.startsWith("VM.");
      })
      .filter((shape) => {
        if (flex === undefined) return true;
        return flex
          ? shape.shape.endsWith(".Flex")
          : !shape.shape.endsWith(".Flex");
      })
      .sort((s1, s2) => {
        return s1.shape.localeCompare(s2.shape);
      });
  } catch (error) {
    exitWithError(`Error: get available shapes ${error.message}`);
  }
}

export async function getTenancyId() {
  const tenancyIdEnv = process.env.OCI_TENANCY;
  const tenancyId = tenancyIdEnv
    ? tenancyIdEnv
    : await question("OCI tenancy: ");
  return tenancyId;
}

export async function searchCompartmentIdByName(
  profile = "DEFAULT",
  compartmentName
) {
  if (!compartmentName) {
    exitWithError("Compartment name required");
  }
  if (compartmentName === "root") {
    return getTenancyId();
  }
  try {
    const { stdout, exitCode, stderr } = await $`oci iam compartment list \
                --compartment-id-in-subtree true \
                --name ${compartmentName} \
                --profile=${profile} \
                --query "data[].id"`;
    if (exitCode !== 0) {
      exitWithError(stderr);
    }
    if (!stdout.length) {
      exitWithError("Compartment name not found");
    }
    const compartmentId = JSON.parse(stdout.trim())[0];
    return compartmentId;
  } catch (error) {
    exitWithError(error.stderr);
  }
}

export async function uploadApiKeyFile(userId, publicKeyPath) {
  if (!userId) {
    exitWithError("User ID required");
  }
  if (!publicKeyPath) {
    exitWithError("Public RSA key required");
  }
  const rsaPublicKeyExists = await fs.pathExists(publicKeyPath);
  if (!rsaPublicKeyExists) {
    exitWithError(`RSA Public key ${publicKeyPath} does not exists`);
  }
  try {
    const { stdout, exitCode, stderr } =
      await $`oci iam user api-key upload --user-id ${userId} --key-file ${publicKeyPath}`;
    if (exitCode !== 0) {
      exitWithError(stderr);
    }
    if (!stdout.length) {
      exitWithError("Compartment name not found");
    }
    const { fingerprint } = JSON.parse(stdout.trim()).data;
    return fingerprint;
  } catch (error) {
    exitWithError(error.stderr);
  }
}

export async function getUserId() {
  const userIdEnv = process.env.OCI_CS_USER_OCID;
  if (userIdEnv) {
    return userIdEnv;
  }
  const userEmail = await question("OCI User email: ");
  const { stdout, exitCode, stderr } = await $`oci iam user list --all`;
  if (exitCode !== 0) {
    exitWithError(stderr);
  }
  if (!stdout.length) {
    exitWithError("User name not found");
  }
  const data = JSON.parse(stdout.trim()).data;
  const userFound = data.find((user) => user.email === userEmail);
  if (!userFound) {
    exitWithError(`User ${userEmail} not found`);
  }
  return userFound.id;
}

export async function createBucket(compartmentId, name) {
  if (!compartmentId) {
    exitWithError(`Compartment Id required to create bucket`);
  }
  if (!name) {
    exitWithError(`Name required to create bucket`);
  }
  const namespace = await getNamespace();
  try {
    const { stdout, exitCode, stderr } = await $`oci os bucket create \
        --namespace-name ${namespace} \
        --compartment-id ${compartmentId} \
        --name ${name}`;
    if (exitCode !== 0) {
      exitWithError(stderr);
    }
    const { fingerprint } = JSON.parse(stdout.trim()).data;
    return fingerprint;
  } catch (error) {
    exitWithError(error.stderr);
  }
}

export async function deleteBucket(name) {
  if (!name) {
    exitWithError(`Name required to create bucket`);
  }
  const namespace = await getNamespace();
  try {
    const { exitCode, stderr } = await $`oci os bucket delete \
      --bucket-name ${name} \
      --namespace-name ${namespace} \
      --empty --force`;
    if (exitCode !== 0) {
      exitWithError(stderr);
    }
    return;
  } catch (error) {
    exitWithError(error.stderr);
  }
}

export async function putObject(bucketName, objectName, filePath) {
  if (!bucketName) {
    exitWithError(`Bucket name required to put an object`);
  }
  if (!objectName) {
    exitWithError(`Object name required to put an object`);
  }
  if (!filePath) {
    exitWithError(`File path required to put an object`);
  }
  const namespace = await getNamespace();
  try {
    const { exitCode, stderr } = await $`oci os object put \
      --force --name ${objectName} \
      -bn ${bucketName} -ns ${namespace} \
      --file ${filePath}`;
    if (exitCode !== 0) {
      exitWithError(stderr);
    }
    return;
  } catch (error) {
    exitWithError(error.stderr);
  }
}

export async function createPARObject(bucketName, objectName, expiration) {
  if (!bucketName) {
    exitWithError(`Bucket name required to create a PAR`);
  }
  if (!objectName) {
    exitWithError(`Object name required to create a PAR`);
  }
  if (!expiration) {
    exitWithError(`RFC 3339 expiration required to create a PAR`);
  }
  const namespace = await getNamespace();

  try {
    const { stdout, exitCode, stderr } = await $`oci os preauth-request create \
        --bucket-name ${bucketName} \
        --namespace-name ${namespace} \
        --name ${objectName}_par \
        --access-type ObjectRead \
        --time-expires "${expiration}" \
        --object-name ${objectName}`;
    if (exitCode !== 0) {
      exitWithError(stderr);
    }
    const fullPath = JSON.parse(stdout.trim()).data["full-path"];
    return fullPath;
  } catch (error) {
    exitWithError(error.stderr);
  }
}

export async function listPARs(bucketName) {
  if (!bucketName) {
    exitWithError(`Bucket name required to list PARs`);
  }
  const namespace = await getNamespace();
  try {
    const { stdout, exitCode, stderr } = await $`oci os preauth-request list \
      --bucket-name ${bucketName} \
      --namespace-name ${namespace} \
      --all`;
    if (exitCode !== 0) {
      exitWithError(stderr);
    }
    if (!stdout.length) return [];
    const pars = JSON.parse(stdout.trim()).data;
    return pars;
  } catch (error) {
    exitWithError(error.stderr);
  }
}

export async function deletePAR(bucketName, id) {
  if (!bucketName) {
    exitWithError(`Bucket name required to delete a PAR`);
  }
  if (!id) {
    exitWithError(`PAR id required to delete a PAR`);
  }
  const namespace = await getNamespace();
  try {
    const { exitCode, stderr } = await $`oci os preauth-request delete \
      --bucket-name ${bucketName} \
      --namespace-name ${namespace} \
      --par-id ${id} --force`;
    if (exitCode !== 0) {
      exitWithError(stderr);
    }
  } catch (error) {
    exitWithError(error.stderr);
  }
}

export async function listBuckets(compartmentId) {
  if (!compartmentId) {
    exitWithError(`Compartment Id required to create bucket`);
  }
  const namespace = await getNamespace();
  try {
    const { stdout, exitCode, stderr } = await $`oci os bucket list \
      --compartment-id ${compartmentId} \
      --namespace-name ${namespace} \
      --all`;
    if (exitCode !== 0) {
      exitWithError(stderr);
    }
    if (!stdout.length) return [];
    const compartmentList = JSON.parse(stdout.trim()).data;
    return compartmentList;
  } catch (error) {
    exitWithError(error.stderr);
  }
}

export async function getBucket(compartmentId, name) {
  if (!compartmentId) {
    exitWithError(`Compartment Id required to create bucket`);
  }
  if (!name) {
    exitWithError(`Name required to create bucket`);
  }
  const listBucket = await listBuckets(compartmentId);
  return listBucket.find((b) => b.name === name);
}

export async function getLatestGenAIModels(
  profile,
  compartmentId,
  regionName,
  vendor = "cohere",
  capability = "TEXT_GENERATION"
) {
  if (!compartmentId) {
    exitWithError(`Compartment Id required to get GenAI models`);
  }
  if (!regionName) {
    exitWithError(`Region name required to get GenAI models`);
  }

  try {
    const { stdout, stderr, exitCode } =
      await $`oci generative-ai model-collection list-models \
    --profile ${profile} \
    --compartment-id ${compartmentId} \
    --region ${regionName}`;

    if (exitCode !== 0) {
      exitWithError(stderr);
    }

    if (!stdout.length) return {};
    const { data } = JSON.parse(stdout.trim());

    const activeCohereModels = where(data.items, {
      "lifecycle-state": "ACTIVE",
      vendor: vendor,
    });

    const filteredByCapatility = activeCohereModels.filter((model) => {
      const { capabilities } = model;
      if (capabilities.length !== 1) return false;
      if (capabilities[0] !== capability) return false;
      return true;
    });

    const latestVersion = max(filteredByCapatility, (item) =>
      parseFloat(item.version)
    );

    return latestVersion;
  } catch (error) {}
}
