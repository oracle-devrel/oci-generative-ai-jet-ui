import { CodeEmbedding, SearchResult, VectorIndexInfo, QueryFilter } from '../types';
import { mockEmbeddings } from '../data/mockData';
import { langchainService } from './langchainService';

// Vector database service that uses LangChain for semantic search
export class VectorDB {
  private isInitialized = false;

  constructor() {
    this.initializeLangChain();
  }

  // Initialize LangChain service with mock data
  private async initializeLangChain(): Promise<void> {
    if (!this.isInitialized) {
      await langchainService.initialize(mockEmbeddings);
      this.isInitialized = true;
    }
  }

  // Upsert embeddings into the vector database
  async upsert(embeddings: CodeEmbedding[]): Promise<{ success: boolean; upserted: number }> {
    await this.initializeLangChain();
    return await langchainService.upsert(embeddings);
  }

  // Query the vector database with natural language
  async query(
    text: string, 
    topK: number = 5, 
    filter?: QueryFilter
  ): Promise<SearchResult[]> {
    await this.initializeLangChain();
    return await langchainService.query(text, topK, filter);
  }

  // Filter embeddings by metadata
  async filter(filter: QueryFilter): Promise<CodeEmbedding[]> {
    await this.initializeLangChain();
    return await langchainService.filter(filter);
  }

  // Get index information
  async describeIndex(): Promise<VectorIndexInfo> {
    await this.initializeLangChain();
    return await langchainService.describeIndex();
  }

  // Get all embeddings (for debugging)
  async getAllEmbeddings(): Promise<CodeEmbedding[]> {
    const documents = await langchainService.getAllDocuments();
    return documents.map(doc => ({
      id: doc.metadata.id,
      content: doc.pageContent,
      embedding: doc.metadata.mockEmbedding || [],
      metadata: {
        fileName: doc.metadata.fileName,
        filePath: doc.metadata.filePath,
        language: doc.metadata.language,
        functionName: doc.metadata.functionName,
        lineStart: doc.metadata.lineStart,
        lineEnd: doc.metadata.lineEnd,
      }
    }));
  }
}

// Singleton instance
export const vectorDB = new VectorDB();