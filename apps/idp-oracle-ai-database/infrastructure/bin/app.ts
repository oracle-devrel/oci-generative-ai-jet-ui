import "source-map-support/register";
import dotenv from "dotenv";
import { App } from "aws-cdk-lib";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { IdpStack } from "../lib/stack.js";

dotenv.config({ path: join(dirname(fileURLToPath(import.meta.url)), "..", "..", ".env") });

function required(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`${name} env var is required (set in .env at repo root)`);
  return v;
}

const app = new App();

new IdpStack(app, "IdpStack", {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION ?? "us-east-1",
  },
  oracleConnectString: required("ORACLE_CONNECT_STRING"),
  oracleUser: required("ORACLE_USER"),
  oraclePassword: required("ORACLE_PASSWORD"),
  oracleWalletLocation: required("ORACLE_WALLET_LOCATION"),
  oracleWalletPassword: required("ORACLE_WALLET_PASSWORD"),
  ociUserOcid: required("OCI_USER_OCID"),
  ociTenancyOcid: required("OCI_TENANCY_OCID"),
  ociCompartmentOcid: required("OCI_COMPARTMENT_OCID"),
  ociFingerprint: required("OCI_FINGERPRINT"),
  ociGenaiRegion: process.env.OCI_GENAI_REGION ?? "eu-frankfurt-1",
  ociGenaiModel: process.env.OCI_GENAI_MODEL ?? "meta.llama-3.3-70b-instruct",
});
