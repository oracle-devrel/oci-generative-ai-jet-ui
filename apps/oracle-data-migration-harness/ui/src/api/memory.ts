export type MemoryMessage = {
  thread_id?: string;
  source_side?: string;
  side?: string;
  role: "user" | "assistant";
  content: string;
  created_at?: string;
};

export async function fetchMemory(
  side: "mongo" | "oracle"
): Promise<{ side: string; count: number; messages: MemoryMessage[] }> {
  const r = await fetch(`/memory/${side}`);
  return r.json();
}
