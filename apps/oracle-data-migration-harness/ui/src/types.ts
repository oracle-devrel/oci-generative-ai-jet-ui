export type Side = "mongo" | "oracle";

export type ChartPayload = {
  type: "bar";
  x: string;
  y: string;
  data: Record<string, any>[];
};

export type ChatMsg = {
  role: "user" | "assistant";
  text: string;
  chart?: ChartPayload;
  tool_statuses?: string[];
};
