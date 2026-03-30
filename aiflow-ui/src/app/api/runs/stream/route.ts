import { readJsonFile } from "@/lib/data-store";
import type { WorkflowRun } from "@/lib/types";

// GET /api/runs/stream — SSE stream for run status updates
// Sends current runs every 3 seconds, closes after 30 seconds
export async function GET() {
  const encoder = new TextEncoder();
  let closed = false;

  const stream = new ReadableStream({
    async start(controller) {
      const sendUpdate = async () => {
        if (closed) return;
        try {
          const runs = await readJsonFile<WorkflowRun[]>("runs.json");
          const event = `data: ${JSON.stringify({ runs, total: runs.length, timestamp: new Date().toISOString() })}\n\n`;
          controller.enqueue(encoder.encode(event));
        } catch {
          // Data file not available
        }
      };

      // Send initial data immediately
      await sendUpdate();

      // Poll every 3 seconds for 30 seconds
      let ticks = 0;
      const interval = setInterval(async () => {
        ticks++;
        if (ticks >= 10 || closed) {
          clearInterval(interval);
          if (!closed) {
            controller.enqueue(encoder.encode("data: [DONE]\n\n"));
            controller.close();
          }
          return;
        }
        await sendUpdate();
      }, 3000);
    },
    cancel() {
      closed = true;
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
