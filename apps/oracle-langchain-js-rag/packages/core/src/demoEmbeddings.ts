import { Embeddings } from "@langchain/core/embeddings";

export class DemoEmbeddings extends Embeddings {
  readonly dimensions = 12;

  private readonly terms = [
    "oracle",
    "database",
    "vector",
    "langchain",
    "javascript",
    "typescript",
    "rag",
    "metadata",
    "api",
    "retrieval",
    "index",
    "application",
  ];

  constructor() {
    super({});
  }

  textToVector(text: string): number[] {
    const lower = text.toLowerCase();
    const vector = this.terms.map((term) => {
      const matches = lower.match(new RegExp(term, "g"));
      return matches ? matches.length : 0;
    });

    for (const token of lower.split(/[^a-z0-9]+/).filter(Boolean)) {
      let bucket = 0;
      for (const char of token) {
        bucket = (bucket + char.charCodeAt(0)) % this.dimensions;
      }
      vector[bucket] = (vector[bucket] ?? 0) + 0.15;
    }

    const norm = Math.sqrt(vector.reduce((sum, value) => sum + value * value, 0)) || 1;
    return vector.map((value) => Number((value / norm).toFixed(6)));
  }

  override async embedQuery(text: string): Promise<number[]> {
    return this.textToVector(text);
  }

  override async embedDocuments(texts: string[]): Promise<number[][]> {
    return texts.map((text) => this.textToVector(text));
  }
}
