import { NextResponse } from "next/server";
import { readJsonFile } from "@/lib/data-store";
import { fetchBackend } from "@/lib/backend";
import type { RagConversation, QueryOutput } from "@/lib/types";

// POST /api/rag/query — try FastAPI chat completions, fallback to mock
export async function POST(request: Request) {
  const body = await request.json();
  const { question, collection, role } = body as {
    question: string;
    collection?: string;
    role?: string;
  };

  if (!question) {
    return NextResponse.json({ error: "question is required" }, { status: 400 });
  }

  // Try Python backend (chat completions endpoint)
  const backend = await fetchBackend<QueryOutput>("/v1/chat/completions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "aszf_rag_chat",
      messages: [{ role: "user", content: question }],
      metadata: { collection: collection || "default", role: role || "baseline" },
    }),
  });
  if (backend) {
    return NextResponse.json(backend.data);
  }

  // Fallback to mock data
  const conversations = await readJsonFile<RagConversation[]>("rag_conversations.json");
  const firstConv = conversations[0];
  const lastAssistant = firstConv?.messages.findLast((m) => m.role === "assistant");

  if (!lastAssistant?.query_output) {
    const fallback: QueryOutput = {
      answer: "A RAG backend jelenleg nem elerheto. Mock valasz a kerdesre: " + question,
      citations: [],
      search_results: [],
      hallucination_score: 0.5,
      processing_time_ms: 0,
      tokens_used: 0,
      cost_usd: 0,
    };
    return NextResponse.json(fallback);
  }

  return NextResponse.json(lastAssistant.query_output);
}
