declare module "oracledb" {
  export type PoolAttributes = {
    user?: string;
    password?: string;
    connectionString?: string;
    poolMin?: number;
    poolMax?: number;
    poolIncrement?: number;
  };

  export type ExecuteOptions = {
    outFormat?: unknown;
  };

  export type ExecuteResult = {
    rows?: Record<string, unknown>[];
  };

  export type Connection = {
    close(): Promise<void>;
    execute(statement: string, binds?: Record<string, unknown>, options?: ExecuteOptions): Promise<ExecuteResult>;
  };

  export type Pool = {
    getConnection(): Promise<Connection>;
  };

  const oracledb: {
    CLOB: unknown;
    OUT_FORMAT_OBJECT: unknown;
    createPool(attributes: PoolAttributes): Promise<Pool>;
    fetchAsString: unknown[];
  };

  export default oracledb;
}
