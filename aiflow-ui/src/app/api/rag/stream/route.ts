import { readJsonFile } from "@/lib/data-store";
import type { RagConversation, QueryOutput } from "@/lib/types";

// POST /api/rag/stream — SSE streaming response for RAG chat
// Streams the answer token-by-token, then sends metadata (citations, scores) at the end
export async function POST(request: Request) {
  const body = await request.json();
  const { question, role } = body as { question: string; role?: string };

  if (!question) {
    return new Response(JSON.stringify({ error: "question is required" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  // Get mock data to simulate streaming
  const conversations = await readJsonFile<RagConversation[]>("rag_conversations.json");
  const firstConv = conversations[0];
  const lastAssistant = firstConv?.messages.findLast((m) => m.role === "assistant");
  const output: QueryOutput = lastAssistant?.query_output || {
    answer: "A RAG backend jelenleg nem elerheto. Mock valasz: " + question,
    citations: [],
    search_results: [],
    hallucination_score: 0.5,
    processing_time_ms: 0,
    tokens_used: 0,
    cost_usd: 0,
  };

  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      // Simulate token-by-token streaming of the answer
      const words = output.answer.split(" ");
      for (let i = 0; i < words.length; i++) {
        const token = (i === 0 ? "" : " ") + words[i];
        const event = `data: ${JSON.stringify({ type: "token", content: token })}\n\n`;
        controller.enqueue(encoder.encode(event));
        // Simulate LLM generation delay (30-80ms per token)
        await new Promise((r) => setTimeout(r, 30 + Math.random() * 50));
      }

      // Send metadata (citations, search results, scores) at the end
      const metadata: Omit<QueryOutput, "answer"> = {
        citations: output.citations,
        search_results: output.search_results,
        hallucination_score: output.hallucination_score,
        processing_time_ms: output.processing_time_ms,
        tokens_used: output.tokens_used,
        cost_usd: output.cost_usd,
      };
      const metaEvent = `data: ${JSON.stringify({ type: "metadata", ...metadata })}\n\n`;
      controller.enqueue(encoder.encode(metaEvent));

      // Signal done
      controller.enqueue(encoder.encode("data: [DONE]\n\n"));
      controller.close();
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
