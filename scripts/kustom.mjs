#!/usr/bin/env zx
import Configstore from "configstore";
import clear from "clear";
import Mustache from "mustache";
import { getOutputValues } from "./lib/terraform.mjs";
import { exitWithError } from "./lib/utils.mjs";

$.verbose = false;

clear();
console.log("Create kustomization configuration...");

const projectName = "genai";

const config = new Configstore(projectName, { projectName });

const compartmentId = config.get("compartmentId");
const namespace = config.get("namespace");
const regionName = config.get("regionName");
const regionKey = config.get("regionKey");
const webVersion = config.get("webVersion");
const appVersion = config.get("appVersion");
const backendVersion = config.get("backendVersion");
const certFullchain = config.get("certFullchain");
const certPrivateKey = config.get("certPrivateKey");
const genAiModelChat = config.get("genAiModelChat");
const genAiModelSummarization = config.get("genAiModelSummarization");

const { db_service, db_password } = await getOutputValues("./deploy/terraform");

await createBackendProperties();
await createProdKustomization();
await copyCerts();
await copyWallet();

const namespaceName = "backend";
await createNamespace(namespaceName);
await createRegistrySecret();

async function createBackendProperties() {
  const backendPropertiesPath = "deploy/k8s/backend/application.yaml";

  const backendPropertiesTemplate = await fs.readFile(
    `${backendPropertiesPath}.mustache`,
    "utf-8"
  );

  const backendPropertiesOutput = Mustache.render(backendPropertiesTemplate, {
    db_service: db_service,
    db_password: db_password,
    path_to_wallet: "/wallet",
    region_name: regionName,
    compartment_ocid: compartmentId,
    genai_model_chat_ocid: genAiModelChat,
    genai_model_summarization_ocid: genAiModelSummarization,
  });

  await fs.writeFile(backendPropertiesPath, backendPropertiesOutput);

  console.log(`File ${chalk.green(backendPropertiesPath)} created`);
}

async function createProdKustomization() {
  const prodKustomizationPath = "deploy/k8s/overlays/prod/kustomization.yaml";

  const prodKustomizationTemplate = await fs.readFile(
    `${prodKustomizationPath}.mustache`,
    "utf-8"
  );

  const prodKustomizationOutput = Mustache.render(prodKustomizationTemplate, {
    region_key: regionKey,
    tenancy_namespace: namespace,
    project_name: projectName,
    app_version: appVersion,
    web_version: webVersion,
    backend_version: backendVersion,
  });

  await fs.writeFile(prodKustomizationPath, prodKustomizationOutput);

  console.log(`File ${chalk.green(prodKustomizationPath)} created`);
}

async function copyCerts() {
  const ingressCertsPath = "deploy/k8s/ingress/.certs";
  await $`mkdir -p ${ingressCertsPath}`;
  await $`cp ${certFullchain} ${ingressCertsPath}/`;
  console.log(`File ${chalk.green(certFullchain)} copied`);
  await $`cp ${certPrivateKey} ${ingressCertsPath}/`;
  console.log(`File ${chalk.green(certPrivateKey)} copied`);
}

async function copyWallet() {
  const backendWalletPath = "deploy/k8s/backend/wallet";
  await $`mkdir -p ${backendWalletPath}`;
  const walletSourcePath = "deploy/terraform/generated/wallet.zip";
  await $`cp ${walletSourcePath} ${backendWalletPath}/`;
  console.log(`File ${chalk.green(walletSourcePath)} copied`);
}

async function createNamespace(namespaceName = "default") {
  try {
    const { exitCode, stdout } =
      await $`KUBECONFIG="deploy/terraform/generated/kubeconfig" \
        kubectl create ns ${namespaceName} -o yaml \
          --dry-run=client | \
          KUBECONFIG="deploy/terraform/generated/kubeconfig" kubectl apply -f -`;
    if (exitCode !== 0) {
      exitWithError("namespace not created");
    } else {
      console.log(
        `Namespace ${chalk.green(
          namespaceName
        )} created on Kubernetes cluster: ${stdout}`
      );
    }
  } catch (error) {
    exitWithError(error.stderr);
  }
}

async function createRegistrySecret() {
  const user = config.get("ocir_user");
  const email = config.get("ocir_user_email");
  const token = config.get("ocir_user_token");
  try {
    const { exitCode, stdout } =
      await $`KUBECONFIG="deploy/terraform/generated/kubeconfig" kubectl \
        create secret docker-registry ocir-secret \
          --save-config \
          --dry-run=client \
          --docker-server=${regionKey}.ocir.io \
          --docker-username=${namespace}/${user} \
          --docker-password=${token} \
          --docker-email=${email} \
          -n ${namespaceName} \
          -o yaml | \
          KUBECONFIG="deploy/terraform/generated/kubeconfig" kubectl apply -f -`;
    if (exitCode !== 0) {
      exitWithError("docker-registry ocir-secret secret not created");
    } else {
      console.log(
        `Secret ${chalk.green(
          "ocir-secret"
        )} created on Kubernetes cluster: ${stdout}`
      );
    }
  } catch (error) {
    exitWithError(error.stderr);
  }
}
