export type InspectPayload = any;

export async function fetchInspect(side: "mongo" | "oracle"): Promise<InspectPayload> {
  const r = await fetch(`/inspect/${side}`);
  return r.json();
}
