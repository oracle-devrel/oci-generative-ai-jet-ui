export type CheckStatus = "PASS" | "READY" | "OPTIONAL" | "MISSING" | "ERROR";

export interface WorkflowStep {
  step: string;
  status: CheckStatus;
  detail: string;
}

export interface RetrievedDocument {
  rank: number;
  distance?: number;
  source: string;
  title: string;
  section: string;
  category: string;
  product: string;
  priority: string;
  audience: string;
  tags: string[];
  snippet: string;
  metadata: Record<string, unknown>;
}

export interface CorpusDocumentSummary {
  id: string;
  source: string;
  title: string;
  section: string;
  category: string;
  product: string;
  priority: string;
  audience: string;
  tags: string[];
  content: string;
  metadata: Record<string, unknown>;
}

export interface CorpusResponse {
  documents: CorpusDocumentSummary[];
  totalDocuments: number;
  totalSources: number;
  embeddingModel: string;
  embeddingDimension: number;
  chunkingStrategy: string;
}

export interface TableColumn {
  column: string;
  type: string;
}

export interface TableIndex {
  index: string;
  type: string;
  category: "vector" | "internal/system";
}

export interface TableInspection {
  rowCount: number;
  columns: TableColumn[];
  indexes: TableIndex[];
}

export interface OracleInspectionResponse {
  tableName: string;
  connected: boolean;
  detail: string;
  inspection?: TableInspection;
}

export interface RagTrace {
  embedding: {
    model: string;
    dimension: number;
    preview: number[];
    note: string;
  };
  retrieval: {
    mode: RetrievalMode;
    tableName: string;
    topK: number;
    fetchK?: number;
    filter: string;
    distanceStrategy: string;
    langchainCall: string;
    representativeSql: string;
  };
  generation: {
    mode: string;
    model: string;
    systemInstruction: string;
  };
  context: string;
}

export type RetrievalMode = "similarity" | "mmr";

export interface AppStatus {
  api: "ok";
  config: {
    oracleConfigured: boolean;
    openAiConfigured: boolean;
    tableName: string;
    createVectorIndex: boolean;
    missingOracleVars: string[];
  };
  database: {
    connected: boolean;
    detail: string;
  };
}

export interface AskRequest {
  question: string;
  k?: number;
  category?: string;
  retrievalMode?: RetrievalMode;
}

export interface AskResponse {
  question: string;
  answer: string;
  tableName: string;
  retrievalMode: RetrievalMode;
  usedLlm: boolean;
  retrieved: RetrievedDocument[];
  summary: WorkflowStep[];
  trace: RagTrace;
}

export interface SeedResponse {
  tableName: string;
  documentsIndexed: number;
  inspection: TableInspection;
  summary: WorkflowStep[];
}

export interface ResetResponse {
  tableName: string;
  dropped: boolean;
  detail: string;
}
