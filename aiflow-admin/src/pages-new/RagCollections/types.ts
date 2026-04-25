/** Mirrors aiflow.api.v1.rag_collections (Sprint S / S144). */

export type EmbedderProfileId = "bge_m3" | "azure_openai" | "openai" | null;

export const EMBEDDER_PROFILE_OPTIONS: Array<{
  value: EmbedderProfileId;
  label: string;
  badgeClass: string;
}> = [
  {
    value: null,
    label: "Default (legacy 1536-dim)",
    badgeClass:
      "bg-yellow-100 text-yellow-900 dark:bg-yellow-900/40 dark:text-yellow-300",
  },
  {
    value: "bge_m3",
    label: "BGE-M3 (Profile A — 1024-dim)",
    badgeClass:
      "bg-green-100 text-green-900 dark:bg-green-900/40 dark:text-green-300",
  },
  {
    value: "azure_openai",
    label: "Azure OpenAI (Profile B)",
    badgeClass:
      "bg-blue-100 text-blue-900 dark:bg-blue-900/40 dark:text-blue-300",
  },
  {
    value: "openai",
    label: "OpenAI (surrogate)",
    badgeClass: "bg-gray-200 text-gray-900 dark:bg-gray-700 dark:text-gray-200",
  },
];

export interface RagCollectionListItem {
  id: string;
  name: string;
  tenant_id: string;
  embedder_profile_id: string | null;
  embedding_dim: number;
  chunk_count: number;
  document_count: number;
  updated_at: string | null;
}

export interface RagCollectionListResponse {
  items: RagCollectionListItem[];
  total: number;
  source: string;
}

export interface RagCollectionDetail extends RagCollectionListItem {
  description: string | null;
  language: string;
  embedding_model: string;
  created_at: string | null;
  config: Record<string, unknown>;
}
