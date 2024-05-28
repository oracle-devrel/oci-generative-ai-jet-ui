#!/usr/bin/env zx
import Configstore from "configstore";
import clear from "clear";
import {
  buildJarGradle,
  cleanGradle,
  getVersionGradle,
} from "./lib/gradle.mjs";
import { getNpmVersion } from "./lib/npm.mjs";
import {
  buildImage,
  tagImage,
  pushImage,
  checkPodmanMachineRunning,
  containerLogin,
} from "./lib/container.mjs";
import { getOutputValues } from "./lib/terraform.mjs";

$.verbose = false;

clear();
console.log("Release latest backend and web version...");

const projectName = "genai";

const config = new Configstore(projectName, { projectName });

const namespace = config.get("namespace");
const regionKey = config.get("regionKey");

const pwdOutput = (await $`pwd`).stdout.trim();
await cd(`${pwdOutput}/web`);
const webVersion = await getNpmVersion();
config.set("webVersion", webVersion);
await cd(`${pwdOutput}/backend`);
const backendVersion = await getVersionGradle();
config.set("backendVersion", backendVersion);
await cd(pwdOutput);

await checkPodmanMachineRunning();

const ocirUrl = `${regionKey}.ocir.io`;

// FIXME use OCI Vault for the token
const { ocir_user, ocir_user_token, ocir_user_email } = await getOutputValues(
  "./deploy/terraform"
);
config.set("ocir_user", ocir_user);
config.set("ocir_user_email", ocir_user_email);
config.set("ocir_user_token", ocir_user_token);

await containerLogin(namespace, ocir_user, ocir_user_token, ocirUrl);
await releaseWeb();
await releaseBackend();

async function releaseWeb() {
  const service = "web";
  await cd(service);
  const imageName = `${projectName}/${service}`;
  await buildImage(`localhost/${imageName}`, webVersion);
  const localImage = `localhost/${imageName}:${webVersion}`;
  const remoteImage = `${ocirUrl}/${namespace}/${imageName}:${webVersion}`;
  await tagImage(localImage, remoteImage);
  await pushImage(remoteImage);
  console.log(`${chalk.green(remoteImage)} pushed`);
  await cd("..");
}

async function releaseBackend() {
  const service = "backend";
  await cd(service);
  await cleanGradle();
  await buildJarGradle();
  const currentVersion = await getVersionGradle();
  const imageName = `${projectName}/${service}`;
  await buildImage(`localhost/${imageName}`, currentVersion);
  const localImage = `localhost/${imageName}:${currentVersion}`;
  const remoteImage = `${ocirUrl}/${namespace}/${imageName}:${currentVersion}`;
  await tagImage(localImage, remoteImage);
  await pushImage(remoteImage);
  console.log(`${chalk.green(remoteImage)} pushed`);
  await cd("..");
}
