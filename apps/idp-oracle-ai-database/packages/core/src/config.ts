import { createPool } from "@idp/db";
import { logger } from "@idp/logger";

export interface AppConfig {
  oracle: {
    connectString: string;
    user: string;
    password: string;
    walletLocation?: string;
    walletPassword?: string;
  };
}

function required(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`${name} env var is required`);
  return v;
}

export function readConfig(): AppConfig {
  const walletLocation = process.env.ORACLE_WALLET_LOCATION;
  const walletPassword = process.env.ORACLE_WALLET_PASSWORD;
  return {
    oracle: {
      connectString: required("ORACLE_CONNECT_STRING"),
      user: required("ORACLE_USER"),
      password: required("ORACLE_PASSWORD"),
      ...(walletLocation ? { walletLocation } : {}),
      ...(walletPassword ? { walletPassword } : {}),
    },
  };
}

let initialized = false;

export async function initConfig(): Promise<AppConfig> {
  const cfg = readConfig();
  if (!initialized) {
    await createPool(cfg.oracle);
    initialized = true;
    logger.info("app config initialized");
  }
  return cfg;
}
