#!/usr/bin/env zx
import { readFile } from "node:fs/promises";
import { parse as iniParse } from "ini";
import Mustache from "mustache";
import Configstore from "configstore";
import inquirer from "inquirer";
import clear from "clear";
import {
  getNamespace,
  getRegions,
  searchCompartmentIdByName,
} from "./lib/oci.mjs";
import { createSSHKeyPair, createSelfSignedCert } from "./lib/crypto.mjs";

$.verbose = false;

clear();
console.log("Set up environment...");

const projectName = "arag";

const config = new Configstore(projectName, { projectName });

await selectProfile();
const profile = config.get("profile");
const tenancyId = config.get("tenancyId");

await setNamespaceEnv();
await setRegionEnv();
const regionName = config.get("regionName");
await setHuggingFaceToken();
await setCompartmentEnv();
const compartmentId = config.get("compartmentId");

await createSSHKeys(projectName);
await createCerts();

await generateTFVars();

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

  if (listSubscribedRegions.length === 1) {
    config.set("regionName", listSubscribedRegions[0].name);
    config.set("regionKey", listSubscribedRegions[0].key);
  } else {
    await inquirer
      .prompt([
        {
          type: "list",
          name: "region",
          message: "Select the region",
          choices: listSubscribedRegions.map((r) => r.name),
          filter(val) {
            return listSubscribedRegions.find((r) => r.name === val);
          },
        },
      ])
      .then((answers) => {
        config.set("regionName", answers.region.name);
        config.set("regionKey", answers.region.key);
      });
  }
}

async function setHuggingFaceToken() {
  await inquirer
    .prompt([
      {
        type: "input",
        name: "huggingfaceToken",
        message: "Hugging Face Token",
      },
    ])
    .then(async (answers) => {
      const huggingfaceToken = answers.huggingfaceToken;
      config.set("huggingfaceToken", huggingfaceToken);
    });
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

async function generateTFVars() {
  const publicKeyContent = config.get("publicKeyContent");
  const sshPrivateKeyPath = config.get("privateKeyPath");
  const certFullchain = config.get("certFullchain");
  const certPrivateKey = config.get("certPrivateKey");
  const compartmentName = config.get("compartmentName");

  const tfVarsPath = "tf/terraform.tfvars";

  const tfvarsTemplate = await fs.readFile(`${tfVarsPath}.mustache`, "utf-8");

  const output = Mustache.render(tfvarsTemplate, {
    region_name: regionName,
    config_file_profile: profile,
    tenancy_id: tenancyId,
    compartment_id: compartmentId,
    cert_fullchain: certFullchain,
    cert_private_key: certPrivateKey,
    ssh_public_key: publicKeyContent,
    ssh_private_key_path: sshPrivateKeyPath,
  });

  console.log(
    `Terraform will deploy resources in ${chalk.green(
      regionName
    )} in compartment ${
      compartmentName ? chalk.green(compartmentName) : chalk.green("root")
    }`
  );

  await fs.writeFile(tfVarsPath, output);

  console.log(`File ${chalk.green(tfVarsPath)} created`);

  console.log(`1. ${chalk.yellow("cd tf")}`);
  console.log(`2. ${chalk.yellow("terraform init")}`);
  console.log(`3. ${chalk.yellow("terraform apply -auto-approve")}`);
}
