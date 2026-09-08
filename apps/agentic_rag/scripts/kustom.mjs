#!/usr/bin/env zx
import Configstore from "configstore";
import clear from "clear";
import Mustache from "mustache";
import { parse, stringify } from "yaml";
import { readFile, writeFile } from "node:fs/promises";
import { exitWithError } from "./lib/utils.mjs";
import { getOutputValues } from "./lib/terraform.mjs";

$.verbose = false;

clear();
console.log("Create kustomization configuration...");

const projectName = "arag";

const config = new Configstore(projectName, { projectName });

const profile = config.get("profile");
const huggingfaceToken = config.get("huggingfaceToken");

const { adb_name, adb_admin_password } = await getOutputValues("./tf");

await addProfileToKubeconfig(profile);

await createNamespace("agentic-rag");
await createHuggingFaceTokenConfigMapFile(huggingfaceToken);
await copyWallet();

async function createNamespace(namespace) {
  try {
    const { exitCode, stdout } =
      await $`KUBECONFIG="tf/generated/kubeconfig" kubectl \
        create namespace ${namespace} \
          -o yaml --dry-run=client --save-config | \
          KUBECONFIG="tf/generated/kubeconfig" kubectl apply -f -`;
    if (exitCode !== 0) {
      exitWithError(`${namespace} namespace not created`);
    } else {
      console.log(chalk.green(stdout));
    }
  } catch (error) {
    exitWithError(error.stderr);
  }
}

async function createHuggingFaceTokenConfigMapFile(huggingfaceToken) {
  const configMapFilePath = "k8s/kustom/demo/config.yaml";

  const ConfigMapTemplate = await fs.readFile(
    `${configMapFilePath}.mustache`,
    "utf-8"
  );

  const output = Mustache.render(ConfigMapTemplate, {
    hugging_face_token: huggingfaceToken,
    adb_username: "ADMIN",
    adb_admin_password: adb_admin_password,
    adb_service_name: `${adb_name}_high`,
    adb_wallet_location: "/app/wallet",
  });

  await fs.writeFile(configMapFilePath, output);

  console.log(`File ${chalk.green(configMapFilePath)} created`);
}

async function addProfileToKubeconfig(profile = "DEFAULT") {
  if (profile === "DEFAULT") return;

  const kubeconfigPath = "./tf/generated/kubeconfig";

  let yamlContent = await readFile(kubeconfigPath, {
    encoding: "utf-8",
  });

  const profileFlag = "--profile";
  const profileValue = profile;

  const kubeconfig = parse(yamlContent);
  const execArgs = kubeconfig.users[0].user.exec.args;
  if (!execArgs.includes("--profile")) {
    kubeconfig.users[0].user.exec.args = [
      ...execArgs,
      profileFlag,
      profileValue,
    ];
    const newKubeconfigContent = stringify(kubeconfig);

    await writeFile(kubeconfigPath, newKubeconfigContent, {
      encoding: "utf-8",
    });
  }
}

async function copyWallet() {
  const walletPath = "k8s/kustom/demo/wallet";
  await $`mkdir -p ${walletPath}`;
  const walletSourcePath = "tf/generated/wallet.zip";
  await $`cp ${walletSourcePath} ${walletPath}/`;
  console.log(`File ${chalk.green(walletSourcePath)} copied`);
}
