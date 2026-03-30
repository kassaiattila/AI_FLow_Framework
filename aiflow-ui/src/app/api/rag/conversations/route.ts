import { NextResponse } from "next/server";
import { readJsonFile } from "@/lib/data-store";
import type { RagConversation } from "@/lib/types";

// GET /api/rag/conversations — list all conversations
export async function GET() {
  const conversations = await readJsonFile<RagConversation[]>("rag_conversations.json");
  return NextResponse.json({ conversations, total: conversations.length });
}
