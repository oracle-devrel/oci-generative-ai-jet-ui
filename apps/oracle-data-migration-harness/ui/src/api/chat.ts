import { fetchEventSource } from "@microsoft/fetch-event-source";
import type { ChartPayload, Side } from "../types";

export async function streamChat(
  side: Side,
  question: string,
  onToken: (t: string) => void,
  onChart: (c: ChartPayload) => void,
  onToolStatus: (s: string) => void,
  onDone: () => void
) {
  await fetchEventSource(`/chat/${side}?q=${encodeURIComponent(question)}`, {
    onmessage(ev) {
      if (ev.event === "token") onToken(ev.data);
      else if (ev.event === "chart") onChart(JSON.parse(ev.data));
      else if (ev.event === "tool_status") onToolStatus(ev.data);
      else if (ev.event === "done") onDone();
    },
  });
}
