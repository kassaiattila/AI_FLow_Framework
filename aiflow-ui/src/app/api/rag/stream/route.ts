import { readJsonFile } from "@/lib/data-store";
import type { RagConversation, QueryOutput } from "@/lib/types";

const BACKEND_URL = process.env.AIFLOW_BACKEND_URL || "http://localhost:8000";

// POST /api/rag/stream — SSE streaming response for RAG chat
// Priority: 1. FastAPI backend (real RAG) → 2. Mock data (labeled as demo)
export async function POST(request: Request) {
  const body = await request.json();
  const { question, role } = body as { question: string; role?: string };

  if (!question) {
    return new Response(JSON.stringify({ error: "question is required" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  // === Priority 1: Try FastAPI backend ===
  let backendAnswer: string | null = null;
  let backendTokens = 0;

  try {
    const res = await fetch(`${BACKEND_URL}/v1/chat/completions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: `aszf-rag:default:${role || "baseline"}`,
        messages: [{ role: "user", content: question }],
      }),
      signal: AbortSignal.timeout(60_000), // RAG pipeline needs more time than default 3s
    });
    if (res.ok) {
      const data = await res.json();
      backendAnswer = data.choices?.[0]?.message?.content || null;
      backendTokens = data.usage?.total_tokens || 0;
      console.log("[rag/stream] Backend answered, tokens:", backendTokens);
    }
  } catch (err) {
    console.log("[rag/stream] Backend unavailable, using mock");
  }

  const isLive = backendAnswer !== null;

  // === Priority 2: Mock fallback ===
  let mockOutput: QueryOutput | null = null;
  if (!isLive) {
    const conversations = await readJsonFile<RagConversation[]>("rag_conversations.json");
    const firstConv = conversations[0];
    const lastAssistant = firstConv?.messages.findLast((m) => m.role === "assistant");
    mockOutput = lastAssistant?.query_output || {
      answer: "RAG backend unavailable. Mock answer for: " + question,
      citations: [],
      search_results: [],
      hallucination_score: 0.5,
      processing_time_ms: 0,
      tokens_used: 0,
      cost_usd: 0,
    };
  }

  const answer = isLive ? backendAnswer! : mockOutput!.answer;
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      // Send source indicator first
      controller.enqueue(
        encoder.encode(`data: ${JSON.stringify({ type: "source", mode: isLive ? "backend" : "demo" })}\n\n`)
      );

      // Stream answer token-by-token
      const words = answer.split(" ");
      for (let i = 0; i < words.length; i++) {
        const token = (i === 0 ? "" : " ") + words[i];
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "token", content: token })}\n\n`));
        // Only simulate delay for mock — real answer already waited for the backend
        if (!isLive) {
          await new Promise((r) => setTimeout(r, 30 + Math.random() * 50));
        }
      }

      // Send metadata at the end
      const metadata: Omit<QueryOutput, "answer"> = isLive
        ? {
            citations: [],
            search_results: [],
            hallucination_score: 0,
            processing_time_ms: 0,
            tokens_used: backendTokens,
            cost_usd: 0,
          }
        : {
            citations: mockOutput!.citations,
            search_results: mockOutput!.search_results,
            hallucination_score: mockOutput!.hallucination_score,
            processing_time_ms: mockOutput!.processing_time_ms,
            tokens_used: mockOutput!.tokens_used,
            cost_usd: mockOutput!.cost_usd,
          };

      controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "metadata", ...metadata })}\n\n`));
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
