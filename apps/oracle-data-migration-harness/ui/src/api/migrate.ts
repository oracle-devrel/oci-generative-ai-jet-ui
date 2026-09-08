import { fetchEventSource } from "@microsoft/fetch-event-source";

export type StageEvent = {
  stage: string;
  status: string;
  narration: string;
  code?: string;
  ddl_preview?: string;
};

export async function startMigration(): Promise<void> {
  await fetch("/migrate", { method: "POST" });
}

export async function streamMigration(onStage: (e: StageEvent) => void, onDone: () => void) {
  await fetchEventSource("/migrate/stream", {
    onmessage(ev) {
      if (ev.event === "stage") onStage(JSON.parse(ev.data));
      else if (ev.event === "done") onDone();
    },
  });
}

export async function resetMigration(): Promise<void> {
  await fetch("/reset", { method: "POST" });
}
