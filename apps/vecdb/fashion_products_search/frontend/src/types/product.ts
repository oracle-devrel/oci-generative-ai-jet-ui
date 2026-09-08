export interface SearchResult {
  id: string;
  similarityScore: number;
  imageUrl: string;
  gender: string;
  masterCategory: string;
  subCategory: string;
  articleType: string;
  baseColour: string;
  season: string;
  year?: number;
  usage: string;
  productDisplayName: string;
  path?: string;
}

export interface SearchFilters {
  gender?: string;
  masterCategory?: string;
}
