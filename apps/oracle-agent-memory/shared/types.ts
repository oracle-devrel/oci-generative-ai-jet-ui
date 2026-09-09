export interface StyleProfile {
  tone: string[];
  sentenceLength: { averageWords: number; habit: string };
  structuralHabits: string[];
  signaturePhrases: string[];
  thingsINeverDo: string[];
  topicsICareAbout: string[];
  platformQuirks: Record<string, string>;
}

export interface ProfileDiff {
  additions: Array<{ field: string; value: unknown; evidence: string }>;
  removals: Array<{ field: string; value: unknown; reason: string }>;
  rationale: string;
}

export interface Post {
  id: string;
  userId: string;
  platform: string;
  topic: string | null;
  content: string;
  createdAt: string;
}

export interface SimilarPost {
  id: string;
  content: string;
  topic: string | null;
  distance: number;
}

export interface DraftRequest {
  userId: string;
  platform: string;
  topic: string;
}

export interface DraftResponse {
  draft: string;
  basedOn: { postId: string; topic: string | null; distance: number }[];
}

export interface SavePostRequest {
  userId: string;
  platform: string;
  topic: string;
  content: string;
}
