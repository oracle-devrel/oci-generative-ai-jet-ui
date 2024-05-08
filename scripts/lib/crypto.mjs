#!/usr/bin/env zx
import { exitWithError } from "./utils.mjs";

export async function createSelfSignedCert(outputPath = ".") {
  await $`mkdir -p ${outputPath}`;
  const keyPath = path.normalize(path.join(outputPath, "tls.key"));
  const certPath = path.normalize(path.join(outputPath, "tls.crt"));
  try {
    await $`openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout ${keyPath} -out ${certPath} -subj "/CN=nginxsvc/O=nginxsvc"`;
    console.log(`Cert Key created: ${chalk.green(keyPath)}`);
    console.log(`Cert created: ${chalk.green(certPath)}`);
  } catch (error) {
    exitWithError(error.stderr);
  }
}

export async function generateRandomString(length = 20) {
  if (length < 12) {
    exitWithError("Password length too short, >= 12 required");
  }
  try {
    const output = (await $`openssl rand -base64 ${length + 15}`).stdout.trim();
    if (output.length) {
      const cleanPassword = output
        .replaceAll("/", "")
        .replaceAll("\\", "")
        .replaceAll("=", "");
      return cleanPassword.slice(0, length);
    } else {
      exitWithError("random string generation failed");
    }
  } catch (error) {
    exitWithError(error.stderr);
  }
}

export async function createRSAKeyPair(outputPath = ".") {
  await $`mkdir -p ${outputPath}`;
  const privateKeyPath = path.normalize(path.join(outputPath, "rsa.pem"));
  const publicKeyPath = path.normalize(path.join(outputPath, "rsa_public.pem"));
  try {
    await $`openssl genrsa -out ${privateKeyPath} 2048`;
    console.log(`RSA Private Key written to: ${chalk.yellow(privateKeyPath)}`);
    await $`openssl rsa -in ${privateKeyPath} -outform PEM -pubout -out ${publicKeyPath}`;
    console.log(`RSA Public Key written to: ${chalk.yellow(publicKeyPath)}`);
  } catch (error) {
    exitWithError(error.stderr);
  }
}

export async function createSSHKeyPair(sshPathParam) {
  const defaultSSHPath = path.join(os.homedir(), ".ssh", "id_rsa");
  const sshPath = sshPathParam || defaultSSHPath;
  try {
    await $`ssh-keygen -t rsa -b 4096 -f ${sshPath} -q -N "" <<<y`;
    return (await $`cat ${sshPath + ".pub"}`).stdout.trim();
  } catch (error) {
    exitWithError(error.stderr);
  }
}
