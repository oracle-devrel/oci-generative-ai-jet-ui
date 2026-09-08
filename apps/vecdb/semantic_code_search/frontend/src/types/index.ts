export interface FileNode {
  id: string;
  name: string;
  type: 'file' | 'folder';
  path: string;
  children?: FileNode[];
  content?: string;
  language?: string;
}
export interface OpenedFile {
  path: string;
  language?: string | null;
  content: string;
}

export interface CodeEmbedding {
  id: string;
  content: string;
  embedding: number[];
  metadata: {
    fileName: string;
    filePath: string;
    language: string;
    functionName?: string;
    lineStart: number;
    lineEnd: number;
  };
}

export interface SearchResult {
  id: string;
  content: string;
  score: number;
  metadata: {
    fileName: string;
    filePath: string;
    language: string;
    functionName?: string;
    lineStart: number;
    lineEnd: number;
  };
}

export interface VectorIndexInfo {
  name: string;
  dimension: number;
  metric: string;
  totalVectors: number;
  createdAt: string;
  lastUpdated: string;
}

export interface QueryFilter {
  language?: string;
  fileName?: string;
  filePath?: string;
}