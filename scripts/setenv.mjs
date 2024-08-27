#!/usr/bin/env zx
import moment from "moment";
import { readFile } from "node:fs/promises";
import { parse as iniParse } from "ini";
import Configstore from "configstore";
import inquirer from "inquirer";
import clear from "clear";
import {
  getLatestGenAIModels,
  getNamespace,
  getRegions,
  searchCompartmentIdByName,
} from "./lib/oci.mjs";
import { createSSHKeyPair, createSelfSignedCert } from "./lib/crypto.mjs";

$.verbose = false;

clear();
console.log("Set up environment...");

const projectName = "genai";

const config = new Configstore(projectName, { projectName });

await selectProfile();
const profile = config.get("profile");
const tenancyId = config.get("tenancyId");

await setNamespaceEnv();
await setRegionEnv();
const regionName = config.get("regionName");
await setCompartmentEnv();
const compartmentId = config.get("compartmentId");

await createSSHKeys(projectName);
await createCerts();
await setLatestGenAIModelChat();
await setLatestGenAIModelSummarization();

console.log(`\nConfiguration file saved in: ${chalk.green(config.path)}`);

async function selectProfile() {
  let ociConfigFile = await readFile(`${os.homedir()}/.oci/config`, {
    encoding: "utf-8",
  });

  const ociConfig = iniParse(ociConfigFile);
  const profileList = Object.keys(ociConfig);

  if (profileList.length === 1) {
    config.set("profile", profileList[0]);
    config.set("tenancyId", ociConfig[profileList[0]].tenancy);
  } else {
    await inquirer
      .prompt([
        {
          type: "list",
          name: "profile",
          message: "Select the OCI Config Profile",
          choices: profileList,
        },
      ])
      .then((answers) => {
        config.set("profile", answers.profile);
        config.set("tenancyId", ociConfig[answers.profile].tenancy);
      });
  }
}

async function setNamespaceEnv() {
  const namespace = await getNamespace(profile);
  config.set("namespace", namespace);
}

async function setRegionEnv() {
  const listSubscribedRegions = (await getRegions(profile, tenancyId)).sort(
    (r1, r2) => r1.isHomeRegion > r2.isHomeRegion
  );

  const listWithGenAISupportingRegions = listSubscribedRegions.filter(
    (r) => r.key === "ord"
  );

  if (listWithGenAISupportingRegions.length === 1) {
    config.set("regionName", listWithGenAISupportingRegions[0].name);
    config.set("regionKey", listWithGenAISupportingRegions[0].key);
  } else {
    await inquirer
      .prompt([
        {
          type: "list",
          name: "region",
          message: "Select the region",
          choices: listWithGenAISupportingRegions.map((r) => r.name),
          filter(val) {
            return listWithGenAISupportingRegions.find((r) => r.name === val);
          },
        },
      ])
      .then((answers) => {
        config.set("regionName", answers.region.name);
        config.set("regionKey", answers.region.key);
      });
  }
}

async function setCompartmentEnv() {
  await inquirer
    .prompt([
      {
        type: "input",
        name: "compartmentName",
        message: "Compartment Name",
        default() {
          return "root";
        },
      },
    ])
    .then(async (answers) => {
      const compartmentName = answers.compartmentName;
      const compartmentId = await searchCompartmentIdByName(
        profile,
        compartmentName || "root"
      );
      config.set("compartmentName", compartmentName);
      config.set("compartmentId", compartmentId);
    });
}

async function createSSHKeys(name) {
  const sshPathParam = path.join(os.homedir(), ".ssh", name);
  const publicKeyContent = await createSSHKeyPair(sshPathParam);
  config.set("privateKeyPath", sshPathParam);
  config.set("publicKeyContent", publicKeyContent);
  config.set("publicKeyPath", `${sshPathParam}.pub`);
  console.log(`SSH key pair created: ${chalk.green(sshPathParam)}`);
}

async function createCerts() {
  const certPath = path.join(__dirname, "..", ".certs");
  await $`mkdir -p ${certPath}`;
  await createSelfSignedCert(certPath);
  config.set("certFullchain", path.join(certPath, "tls.crt"));
  config.set("certPrivateKey", path.join(certPath, "tls.key"));
}

async function setLatestGenAIModelChat() {
  const latestVersionModel = await getLatestGenAIModels(
    profile,
    compartmentId,
    regionName,
    "cohere",
    "TEXT_GENERATION"
  );

  const { id, vendor: vendorName, version, capabilities } = latestVersionModel;
  const displayName = latestVersionModel["display-name"];
  const timeCreated = moment(latestVersionModel["time-created"]).fromNow();
  console.log(
    `Using GenAI Model ${chalk.green(vendorName)}:${chalk.green(
      version
    )} (${chalk.green(displayName)}) with ${chalk.green(
      capabilities.join(",")
    )} created ${timeCreated}`
  );

  config.set("genAiModelChat", id);
}

async function setLatestGenAIModelSummarization() {
  const latestVersionModel = await getLatestGenAIModels(
    profile,
    compartmentId,
    regionName,
    "cohere",
    "TEXT_SUMMARIZATION"
  );

  const { id, vendor: vendorName, version, capabilities } = latestVersionModel;
  const displayName = latestVersionModel["display-name"];
  const timeCreated = moment(latestVersionModel["time-created"]).fromNow();
  console.log(
    `Using GenAI Model ${chalk.green(vendorName)}:${chalk.green(
      version
    )} (${chalk.green(displayName)}) with ${chalk.green(
      capabilities.join(",")
    )} created ${timeCreated}`
  );

  config.set("genAiModelSummarization", id);
}
