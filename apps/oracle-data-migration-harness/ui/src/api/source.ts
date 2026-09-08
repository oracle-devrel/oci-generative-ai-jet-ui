export type SourceInfo = {
  kind: string;
  uri: string;
  database: string;
  collection: string;
  status: string;
  document_count?: number;
  error?: string;
};

export async function fetchSource(): Promise<SourceInfo> {
  const r = await fetch("/source");
  return r.json();
}

export async function testSource(
  payload: Pick<SourceInfo, "uri" | "database" | "collection">
): Promise<any> {
  const r = await fetch("/source/test", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return r.json();
}

export async function connectSource(
  payload: Pick<SourceInfo, "uri" | "database" | "collection">
): Promise<any> {
  const r = await fetch("/source/connect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return r.json();
}

export async function disconnectSource(): Promise<any> {
  const r = await fetch("/source/disconnect", { method: "POST" });
  return r.json();
}
