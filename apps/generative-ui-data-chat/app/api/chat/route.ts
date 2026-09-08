import { NextResponse } from "next/server";
import { ZodError } from "zod";

import { runDataChat } from "@/lib/data-chat";
import { DataChatApiRequestSchema } from "@/lib/schemas";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const encoder = new TextEncoder();

function wantsStream(request: Request) {
  return request.headers.get("accept")?.includes("text/event-stream") ?? false;
}

function encodeEvent(event: string, data: unknown) {
  return encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
}

export async function POST(request: Request) {
  try {
    const body = DataChatApiRequestSchema.parse(await request.json());

    if (wantsStream(request)) {
      let isClosed = false;
      const markClosed = () => {
        isClosed = true;
      };

      const stream = new ReadableStream<Uint8Array>({
        start(controller) {
          const safeEnqueue = (event: string, data: unknown) => {
            if (isClosed) {
              return;
            }

            try {
              controller.enqueue(encodeEvent(event, data));
            } catch {
              markClosed();
            }
          };
          const closeOnce = () => {
            if (isClosed) {
              return;
            }

            markClosed();
            try {
              controller.close();
            } catch {
              // The client may have already closed the stream.
            }
          };

          request.signal.addEventListener("abort", markClosed, { once: true });

          void runDataChat(body.message, {
            onProgress: (progress) => {
              safeEnqueue("status", progress);
            }
          })
            .then((response) => {
              safeEnqueue("complete", response);
            })
            .catch((error) => {
              const message = error instanceof Error ? error.message : "Unknown data chat error";
              safeEnqueue("error", { error: message });
            })
            .finally(closeOnce);
        },
        cancel() {
          markClosed();
        }
      });

      return new Response(stream, {
        headers: {
          "Cache-Control": "no-cache, no-transform",
          Connection: "keep-alive",
          "Content-Type": "text/event-stream; charset=utf-8",
          "X-Accel-Buffering": "no"
        }
      });
    }

    const response = await runDataChat(body.message);

    return NextResponse.json(response);
  } catch (error) {
    const status = error instanceof ZodError ? 400 : 500;
    const message = error instanceof Error ? error.message : "Unknown data chat error";

    return NextResponse.json(
      {
        error: message
      },
      { status }
    );
  }
}
