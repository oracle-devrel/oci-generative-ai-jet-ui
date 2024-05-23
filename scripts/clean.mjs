#!/usr/bin/env zx
import Configstore from "configstore";
import clear from "clear";

$.verbose = false;

clear();
console.log(
  "Clean up config files, certs, ssh keys and Object Storage bucket..."
);

const projectName = "genai";

const config = new Configstore(projectName, { projectName });

const privateKeyPath = config.get("privateKeyPath");
await $`rm -f ${privateKeyPath}`;
const publicKeyPath = config.get("publicKeyPath");
await $`rm -f ${publicKeyPath}`;

const certPath = path.join(__dirname, "..", ".certs");
await $`rm -rf ${certPath}`;

await $`rm -f deploy/k8s/backend/application.yaml`;
await $`rm -f deploy/k8s/overlays/prod/kustomization.yaml`;

const certsK8sPath = "deploy/k8s/ingress/.certs";
await $`rm -rf ${certsK8sPath}`;
console.log(`Files in ${chalk.green(certsK8sPath)} deleted`);
const walletK8sPath = "deploy/k8s/backend/wallet";
await $`rm -rf ${walletK8sPath}`;
console.log(`Files in ${chalk.green(walletK8sPath)} deleted`);

// TODO delete images pushed
// ${regionKey}.ocir.io/${namespace}/${projectName}/web:${webVersion}
// ${regionKey}.ocir.io/${namespace}/${projectName}/backend:${backendBersion}

await $`rm -rf ./.artifacts`;
await $`rm -rf ./deploy/terraform/generated/wallet`;

config.clear();
