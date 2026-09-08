export type Assessment = {
  mode: string;
  document_count: number;
  sample_size: number;
  source: any;
  fields: any[];
  vectors: any[];
  strategy: Record<string, any>;
  warnings: string[];
};

export async function fetchAssessment(): Promise<Assessment> {
  const r = await fetch("/assess");
  return r.json();
}
