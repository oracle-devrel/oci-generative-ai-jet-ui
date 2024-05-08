# OCI ZX Scripts

## Usage

From the root folder of your project, download the scripts folder:

```sh
wget -cO - \
    https://github.com/vmleon/oci-zx-scripts/archive/refs/heads/main.zip > scripts.zip \
    && unzip scripts.zip -d scripts \
    && rm scripts.zip \
    && mv scripts/oci-zx-scripts-main scripts/lib
```

## Example

Create a `setenv.mjs` script to prepare environment:

```sh
touch scripts/setenv.mjs
```

Use the following example:

```js
#!/usr/bin/env zx

import { getNamespace } from "./lib/oci.mjs";
const shell = process.env.SHELL | "/bin/zsh";
$.shell = shell;
$.verbose = false;

console.log("Check fake dependencies...");
const dependencies = ["git", "unzip"];
const namespace = await getNamespace();
console.log(namespace);
```

Run the script:

```sh
npx zx scripts/setenv.mjs
```

## Create new functions

```javascript
#!/usr/bin/env zx
import { exitWithError } from "./utils.mjs";

export async function example() {
  try {
    const { stdout, exitCode, stderr } = await $`pwd`;
    if (exitCode !== 0) {
      exitWithError(stderr);
    }
    return stdout.trim();
  } catch (error) {
    exitWithError(error.stderr);
  }
}
```

## Get Region example

```javascript
import { getRegions } from "./lib/oci.mjs";
import { setVariableFromEnvOrPrompt, printRegionNames } from "./lib/utils.mjs";

const regions = await getRegions();
const regionName = await setVariableFromEnvOrPrompt(
  "OCI_REGION",
  "OCI Region name",
  async () => printRegionNames(regions)
);
const { key } = regions.find((r) => r.name === regionName);
const url = `${key}.ocir.io`;
console.log(url);
```

## Release Example

```javascript
#!/usr/bin/env zx
import {
  getVersion,
  getNamespace,
  printRegionNames,
  setVariableFromEnvOrPrompt,
} from "./lib/utils.mjs";
import { buildImage, tagImage, pushImage } from "./lib/container.mjs";
import { buildWeb } from "./lib/npm.mjs";
import {
  buildJarGradle,
  cleanGradle,
  getVersionGradle,
} from "./lib/gradle.mjs";
import { getRegions } from "./lib/oci.mjs";

const shell = process.env.SHELL | "/bin/zsh";
$.shell = shell;
$.verbose = false;

const { a, _ } = argv;
const [action] = _;

const project = "project_name";
const namespace = await getNamespace();

const regions = await getRegions();
const regionName = await setVariableFromEnvOrPrompt(
  "OCI_REGION",
  "OCI Region name",
  () => printRegionNames(regions)
);
const { key } = regions.find((r) => r.name === regionName);
const ocirUrl = `${key}.ocir.io`;

if (action === "web") {
  await releaseNpm("web");
  process.exit(0);
}

if (action === "backend") {
  await releaseGradle("backend");
  process.exit(0);
}

if (a || action === "all") {
  await releaseNpm("web");
  await releaseGradle("backend");
  process.exit(0);
}

console.log("Usage:");
console.log("\tnpx zx scripts/release.mjs all");
console.log("\tnpx zx scripts/release.mjs -a");
console.log("\tnpx zx scripts/release.mjs web");
console.log("\tnpx zx scripts/release.mjs backend");

async function releaseNpm(service) {
  await cd(service);
  const currentVersion = await getVersion();
  if (service === "web") {
    await buildWeb();
  }
  const image_name = `${project}/${service}`;
  await buildImage(`localhost/${image_name}`, currentVersion);
  const local_image = `localhost/${image_name}:${currentVersion}`;
  const remote_image = `${ocirUrl}/${namespace}/${image_name}:${currentVersion}`;
  await tagImage(local_image, remote_image);
  await pushImage(remote_image);
  console.log(`Released: ${chalk.yellow(remote_image)}`);
  await cd("..");
}
async function releaseGradle(service) {
  await cd(service);
  await cleanGradle();
  await buildJarGradle();
  const currentVersion = await getVersionGradle();
  const image_name = `${project}/${service}`;
  await buildImage(`localhost/${image_name}`, currentVersion);
  const local_image = `localhost/${image_name}:${currentVersion}`;
  const remote_image = `${ocirUrl}/${namespace}/${image_name}:${currentVersion}`;
  await tagImage(local_image, remote_image);
  await pushImage(remote_image);
  console.log(`Released: ${chalk.yellow(remote_image)}`);
  await cd("..");
}
```

## Create RSA

```javascript
#!/usr/bin/env zx

import { getUserId, uploadApiKeyFile } from "./lib/oci.mjs";
import { createRSAKeyPair } from "./lib/tls.mjs";

const shell = process.env.SHELL | "/bin/zsh";
$.shell = shell;
$.verbose = false;

async function createUserDetails() {
  console.log("Generate RSA key pair...");

  const userId = await getUserId();

  properties = {
    ...properties,
    userId,
  };

  const rsaPath = "./.rsa";
  const prevKeyExists = await fs.pathExists(path.join(rsaPath, "rsa.pem"));
  if (prevKeyExists) {
    console.log(`${chalk.yellow("Existing RSA key pair ")} on ${rsaPath}.`);
  } else {
    await createRSAKeyPair(rsaPath);
    const apikeyFingerprint = await uploadApiKeyFile(
      userId,
      path.join(rsaPath, "rsa_public.pem")
    );
    properties = { ...properties, rsaPath, apikeyFingerprint };
  }
  console.log();
}
```

## Use .env.json

```javascript
#!/usr/bin/env zx

import {
  getNamespace,
  writeEnvJson,
  generateRandomString,
  readEnvJson,
} from "./lib/utils.mjs";
import { getTenancyId } from "./lib/oci.mjs";

const shell = process.env.SHELL | "/bin/zsh";
$.shell = shell;
$.verbose = false;

let properties = await readEnvJson();

const namespace = await getNamespace();
const tenancyId = await getTenancyId();
properties = { ...properties, namespace, tenancyId };
await writeEnvJson(properties);

const generatedPassword = await generateRandomString();
properties = { ...properties, generatedPassword };

await writeEnvJson(properties);
```

```javascript
#!/usr/bin/env zx

import { readEnvJson } from "./lib/utils.mjs";

const shell = process.env.SHELL | "/bin/zsh";
$.shell = shell;
$.verbose = false;

const { namespace } = await readEnvJson();
```

```javascript
#!/usr/bin/env zx

import { setVariableFromEnvOrPrompt } from "./lib/utils.mjs";
import { searchCompartmentIdByName } from "./lib/oci.mjs";

const shell = process.env.SHELL | "/bin/zsh";
$.shell = shell;
$.verbose = false;

const compartmentName = await setVariableFromEnvOrPrompt(
  "COMPARTMENT_NAME",
  "Compartment Name (root)"
);

const compartmentId = await searchCompartmentIdByName(
  compartmentName || "root"
);
```

## Read Terraform Output

```javascript
#!/usr/bin/env zx

import { getOutputValues } from "./lib/terraform.mjs";

const shell = process.env.SHELL | "/bin/zsh";
$.shell = shell;
$.verbose = false;

const tfOutput = await getOutputValues("./terraform");

console.log(tfOutput);
```
