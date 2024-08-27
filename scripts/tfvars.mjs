#!/usr/bin/env zx
import Mustache from "mustache";
import Configstore from "configstore";
import clear from "clear";

$.verbose = false;

clear();
console.log("Create terraform.tfvars...");

const projectName = "genai";

const config = new Configstore(projectName, { projectName });

await generateTFVars();

async function generateTFVars() {
  const compartmentId = config.get("compartmentId");
  const compartmentName = config.get("compartmentName");
  const profile = config.get("profile");
  const regionName = config.get("regionName");
  const tenancyId = config.get("tenancyId");
  const publicKeyContent = config.get("publicKeyContent");
  const sshPrivateKeyPath = config.get("privateKeyPath");
  const certFullchain = config.get("certFullchain");
  const certPrivateKey = config.get("certPrivateKey");

  const tfVarsPath = "deploy/terraform/terraform.tfvars";

  const tfvarsTemplate = await fs.readFile(`${tfVarsPath}.mustache`, "utf-8");

  const output = Mustache.render(tfvarsTemplate, {
    tenancyId,
    regionName,
    compartmentId,
    profile,
    ssh_public_key: publicKeyContent,
    ssh_private_key_path: sshPrivateKeyPath,
    cert_fullchain: certFullchain,
    cert_private_key: certPrivateKey,
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

  console.log(`1. ${chalk.yellow("cd deploy/terraform/")}`);
  console.log(`2. ${chalk.yellow("terraform init")}`);
  console.log(`3. ${chalk.yellow("terraform apply -auto-approve")}`);
}
