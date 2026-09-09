type Level = "debug" | "info" | "warn" | "error";

const LEVEL_ORDER: Record<Level, number> = { debug: 10, info: 20, warn: 30, error: 40 };

const envLevel = (process.env.LOG_LEVEL ?? "info") as Level;
const threshold = LEVEL_ORDER[envLevel] ?? LEVEL_ORDER.info;

function emit(level: Level, message: string, fields: Record<string, unknown>): void {
  if (LEVEL_ORDER[level] < threshold) return;
  const record = {
    timestamp: new Date().toISOString(),
    level,
    message,
    ...fields,
  };
  const line = JSON.stringify(record);
  if (level === "error") {
    console.error(line);
  } else if (level === "warn") {
    console.warn(line);
  } else {
    console.log(line);
  }
}

export interface Logger {
  debug(message: string, fields?: Record<string, unknown>): void;
  info(message: string, fields?: Record<string, unknown>): void;
  warn(message: string, fields?: Record<string, unknown>): void;
  error(message: string, fields?: Record<string, unknown>): void;
  child(bindings: Record<string, unknown>): Logger;
}

export function createLogger(bindings: Record<string, unknown> = {}): Logger {
  return {
    debug: (m, f) => emit("debug", m, { ...bindings, ...f }),
    info: (m, f) => emit("info", m, { ...bindings, ...f }),
    warn: (m, f) => emit("warn", m, { ...bindings, ...f }),
    error: (m, f) => emit("error", m, { ...bindings, ...f }),
    child: (extra) => createLogger({ ...bindings, ...extra }),
  };
}

export const logger = createLogger();
