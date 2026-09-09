import { OpenAIEmbeddings } from '@langchain/openai';
import { MemoryVectorStore } from 'langchain/vectorstores/memory';
import { Document } from 'langchain/document';
import { CodeEmbedding, SearchResult, VectorIndexInfo } from '../types';

// LangChain-based semantic search service
export class LangChainVectorService {
  private vectorStore: MemoryVectorStore | null = null;
  private embeddings: OpenAIEmbeddings;
  private documents: Document[] = [];
  private isInitialized = false;

  constructor() {
    // Initialize OpenAI embeddings with environment variable
    const apiKey = import.meta.env.VITE_OPENAI_API_KEY;
    
    if (apiKey) {
      this.embeddings = new OpenAIEmbeddings({
        openAIApiKey: apiKey,
        modelName: 'text-embedding-ada-002',
      });
    } else {
      // If no API key is provided, we'll use mock embeddings
      console.warn('⚠️ No OpenAI API key found. Using mock embeddings for demo.');
      this.embeddings = new OpenAIEmbeddings({
        openAIApiKey: 'mock-key', // This will fail but we'll catch it
        modelName: 'text-embedding-ada-002',
      });
    }
  }

  // Initialize the vector store with code embeddings
  async initialize(codeEmbeddings: CodeEmbedding[]): Promise<void> {
    console.log('🚀 LangChain: Initializing vector store...', { count: codeEmbeddings.length });
    
    // Check if we have a valid API key
    const apiKey = import.meta.env.VITE_OPENAI_API_KEY;
    if (!apiKey) {
      console.log('🔄 LangChain: No API key provided, using mock vector store');
      await this.initializeMockVectorStore(codeEmbeddings);
      return;
    }
    
    try {
      // Convert code embeddings to LangChain documents
      this.documents = codeEmbeddings.map(embedding => new Document({
        pageContent: embedding.content,
        metadata: {
          id: embedding.id,
          fileName: embedding.metadata.fileName,
          filePath: embedding.metadata.filePath,
          language: embedding.metadata.language,
          functionName: embedding.metadata.functionName,
          lineStart: embedding.metadata.lineStart,
          lineEnd: embedding.metadata.lineEnd,
        }
      }));

      // Create vector store from documents
      this.vectorStore = await MemoryVectorStore.fromDocuments(
        this.documents,
        this.embeddings
      );

      this.isInitialized = true;
      console.log('✅ LangChain: Vector store initialized successfully');
    } catch (error) {
      console.error('❌ LangChain: Failed to initialize vector store:', error);
      // Fallback to mock embeddings for demo
      await this.initializeMockVectorStore(codeEmbeddings);
    }
  }

  // Fallback mock initialization for demo purposes
  private async initializeMockVectorStore(codeEmbeddings: CodeEmbedding[]): Promise<void> {
    console.log('🔄 LangChain: Using mock vector store for demo');
    
    // Create mock documents
    this.documents = codeEmbeddings.map(embedding => new Document({
      pageContent: embedding.content,
      metadata: {
        id: embedding.id,
        fileName: embedding.metadata.fileName,
        filePath: embedding.metadata.filePath,
        language: embedding.metadata.language,
        functionName: embedding.metadata.functionName,
        lineStart: embedding.metadata.lineStart,
        lineEnd: embedding.metadata.lineEnd,
        // Add mock similarity score for demo
        mockEmbedding: embedding.embedding,
      }
    }));

    this.isInitialized = true;
  }

  // Upsert new documents into the vector store
  async upsert(codeEmbeddings: CodeEmbedding[]): Promise<{ success: boolean; upserted: number }> {
    console.log('🔄 LangChain: Upserting documents...', { count: codeEmbeddings.length });
    
    if (!this.isInitialized) {
      await this.initialize(codeEmbeddings);
      return { success: true, upserted: codeEmbeddings.length };
    }

    try {
      const newDocuments = codeEmbeddings.map(embedding => new Document({
        pageContent: embedding.content,
        metadata: {
          id: embedding.id,
          fileName: embedding.metadata.fileName,
          filePath: embedding.metadata.filePath,
          language: embedding.metadata.language,
          functionName: embedding.metadata.functionName,
          lineStart: embedding.metadata.lineStart,
          lineEnd: embedding.metadata.lineEnd,
        }
      }));

      if (this.vectorStore) {
        await this.vectorStore.addDocuments(newDocuments);
      }
      
      this.documents.push(...newDocuments);
      
      console.log('✅ LangChain: Upsert completed', { upserted: codeEmbeddings.length });
      return { success: true, upserted: codeEmbeddings.length };
    } catch (error) {
      console.error('❌ LangChain: Upsert failed:', error);
      return { success: false, upserted: 0 };
    }
  }

  // Query the vector store using natural language
  async query(
    text: string, 
    topK: number = 5, 
    filter?: { language?: string; fileName?: string; filePath?: string }
  ): Promise<SearchResult[]> {
    console.log('🔍 LangChain: Querying vector store...', { text, topK, filter });
    
    if (!this.isInitialized) {
      throw new Error('Vector store not initialized');
    }

    try {
      let results: Document[] = [];

      if (this.vectorStore) {
        // Use LangChain similarity search
        results = await this.vectorStore.similaritySearch(text, topK);
      } else {
        // Fallback to mock similarity calculation
        results = this.performMockSimilaritySearch(text, topK);
      }

      // Apply filters if provided
      if (filter) {
        results = results.filter(doc => {
          if (filter.language && doc.metadata.language !== filter.language) return false;
          if (filter.fileName && !doc.metadata.fileName.includes(filter.fileName)) return false;
          if (filter.filePath && !doc.metadata.filePath.includes(filter.filePath)) return false;
          return true;
        });
      }

      // Convert to SearchResult format
      const searchResults: SearchResult[] = results.map((doc, index) => ({
        id: doc.metadata.id,
        content: doc.pageContent,
        score: this.calculateMockScore(text, doc.pageContent, index),
        metadata: {
          fileName: doc.metadata.fileName,
          filePath: doc.metadata.filePath,
          language: doc.metadata.language,
          functionName: doc.metadata.functionName,
          lineStart: doc.metadata.lineStart,
          lineEnd: doc.metadata.lineEnd,
        }
      }));

      console.log('🎯 LangChain: Query completed', { 
        resultsFound: searchResults.length,
        topScore: searchResults[0]?.score 
      });

      return searchResults;
    } catch (error) {
      console.error('❌ LangChain: Query failed:', error);
      return [];
    }
  }

  // Mock similarity search for demo purposes
  private performMockSimilaritySearch(query: string, topK: number): Document[] {
    const queryLower = query.toLowerCase();
    
    // Score documents based on keyword matching
    const scoredDocs = this.documents.map(doc => {
      const content = doc.pageContent.toLowerCase();
      const metadata = JSON.stringify(doc.metadata).toLowerCase();
      
      let score = 0;
      const queryWords = queryLower.split(' ');
      
      queryWords.forEach(word => {
        if (content.includes(word)) score += 2;
        if (metadata.includes(word)) score += 1;
      });
      
      return { doc, score };
    });

    // Sort by score and return top K
    return scoredDocs
      .sort((a, b) => b.score - a.score)
      .slice(0, topK)
      .map(item => item.doc);
  }

  // Calculate mock similarity score
  private calculateMockScore(query: string, content: string, index: number): number {
    const queryLower = query.toLowerCase();
    const contentLower = content.toLowerCase();
    
    let score = 0;
    const queryWords = queryLower.split(' ');
    
    queryWords.forEach(word => {
      if (contentLower.includes(word)) {
        score += 0.2;
      }
    });
    
    // Add some variance based on position
    score = Math.max(0.1, score - (index * 0.05));
    return Math.min(1, score);
  }

  // Filter documents by metadata
  async filter(filterCriteria: { language?: string; fileName?: string; filePath?: string }): Promise<CodeEmbedding[]> {
    console.log('🔧 LangChain: Filtering documents...', filterCriteria);
    
    const filtered = this.documents.filter(doc => {
      if (filterCriteria.language && doc.metadata.language !== filterCriteria.language) return false;
      if (filterCriteria.fileName && !doc.metadata.fileName.includes(filterCriteria.fileName)) return false;
      if (filterCriteria.filePath && !doc.metadata.filePath.includes(filterCriteria.filePath)) return false;
      return true;
    });

    // Convert back to CodeEmbedding format
    const codeEmbeddings: CodeEmbedding[] = filtered.map(doc => ({
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

    console.log('✅ LangChain: Filter completed', { 
      originalCount: this.documents.length,
      filteredCount: codeEmbeddings.length 
    });

    return codeEmbeddings;
  }

  // Get vector store information
  async describeIndex(): Promise<VectorIndexInfo> {
    console.log('📊 LangChain: Describing vector index...');
    
    const indexInfo: VectorIndexInfo = {
      name: 'langchain_code_search_index',
      dimension: 1536, // OpenAI ada-002 embedding dimension
      metric: 'cosine',
      totalVectors: this.documents.length,
      createdAt: '2024-01-15T10:00:00Z',
      lastUpdated: new Date().toISOString()
    };

    console.log('📋 LangChain: Index info retrieved', indexInfo);
    return indexInfo;
  }

  // Get all documents (for debugging)
  async getAllDocuments(): Promise<Document[]> {
    return [...this.documents];
  }
}

// Singleton instance
export const langchainService = new LangChainVectorService();