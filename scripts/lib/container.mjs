#!/usr/bin/env zx
import { exitWithError } from "./utils.mjs";

export async function whichContainerEngine() {
  try {
    const dockerPath = await which("docker");
    return !dockerPath ? "podman" : "docker";
  } catch (err) {
    return "podman";
  }
}

const ce = await whichContainerEngine();

export async function checkPodmanMachineRunning() {
  if (ce === "podman") {
    const isMachineRunning = (
      await $`podman machine info --format {{.Host.MachineState}}`
    ).stdout.trim();
    if (isMachineRunning === "Stopped") {
      console.log(
        `Run ${chalk.yellow("podman machine start")} before continue`
      );
      exitWithError("Podman machine stopped");
    } else {
      console.log(`${chalk.green("[ok]")} podman machine running`);
    }
  }
}

export async function containerLogin(namespace, user, token, url) {
  try {
    const { stdout, stderr, exitCode } =
      await $`${ce} login -u ${namespace}/${user} -p ${token} ${url}`;
    if (exitCode == 0) {
      console.log(`${chalk.yellow(url)}: ${chalk.green(stdout.trim())}`);
    } else {
      console.error(chalk.red(stderr.trim()));
    }
  } catch (error) {
    console.error(chalk.red(error.stderr.trim()));
    const yellowUserString = chalk.yellow(user);
    exitWithError(
      `Review the user ${yellowUserString} and token pair, and try again.`
    );
  }
}

export async function tagImage(local, remote) {
  console.log(`${ce} tag ${local} ${remote}`);
  try {
    await $`${ce} tag ${local} ${remote}`;
  } catch (error) {
    exitWithError(error.stderr);
  }
}

export async function pushImage(remote) {
  console.log(`${ce} push ${remote}`);
  try {
    await $`${ce} push ${remote}`;
  } catch (error) {
    exitWithError(error.stderr);
  }
}

export async function buildImage(name, version) {
  console.log(`${ce} build . -t ${name}:${version}`);
  try {
    await $`${ce} build . -t ${name}:${version}`;
  } catch (error) {
    exitWithError(error.stderr);
  }
}
