/** Shared types for the ChatPanel component family. */

export interface ChatSource {
  text: string;
  score: number;
  document_title?: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: ChatSource[];
  responseTime?: number;
  timestamp: number;
  model?: string;
}

export interface QueryResponse {
  query_id: string;
  question: string;
  answer: string;
  sources: ChatSource[];
  response_time_ms: number;
  cost_usd: number;
  tokens_used?: number;
  model_used?: string;
  source: string;
}

export interface ChatPanelProps {
  collections: { id: string; name: string }[];
  collectionId?: string;
}

export const AVAILABLE_MODELS = [
  { id: "openai/gpt-4o", label: "GPT-4o" },
  { id: "openai/gpt-4o-mini", label: "GPT-4o Mini" },
  { id: "openai/gpt-4.1", label: "GPT-4.1" },
  { id: "openai/gpt-4.1-mini", label: "GPT-4.1 Mini" },
  { id: "anthropic/claude-sonnet-4-20250514", label: "Claude Sonnet 4" },
  { id: "anthropic/claude-haiku-4-20250514", label: "Claude Haiku 4" },
] as const;
