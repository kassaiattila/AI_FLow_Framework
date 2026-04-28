/**
 * AIFlow AszfChat — Sprint X / SX-4.
 *
 * Professional management surface for the ASZF RAG chat. Replaces the
 * previous stateless minimalist page with a three-pane layout:
 *
 *   - Left sidebar: per-tenant conversation history (sorted updated_at DESC).
 *   - Top bar:      persona switcher (baseline/expert/mentor), per-tenant
 *                   collection picker, cumulative cost meter, transcript
 *                   export.
 *   - Center:       turn stream with citation cards + cost chips per
 *                   assistant turn + persona-change markers.
 *
 * Backed by:
 *   - GET/POST /api/v1/conversations               (sidebar history)
 *   - GET     /api/v1/conversations/{id}           (turn replay)
 *   - POST    /api/v1/conversations/{id}/turns     (persistence)
 *   - POST    /api/v1/aszf/chat                    (retrieval w/ citations)
 *   - GET     /api/v1/rag-collections              (collection picker)
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslate } from "../lib/i18n";
import { fetchApi, ApiClientError } from "../lib/api-client";
import { PageLayout } from "../layout/PageLayout";

// ---------------------------------------------------------------------------
// Types — mirror src/aiflow/services/conversations/schemas.py
// ---------------------------------------------------------------------------

type Persona = "baseline" | "expert" | "mentor";
type Role = "user" | "assistant";

interface Citation {
  source_id: string;
  title?: string;
  snippet?: string;
  score?: number;
}

interface ConversationSummary {
  id: string;
  tenant_id: string;
  created_by: string;
  persona: Persona;
  collection_name: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

interface TurnDetail {
  id: string;
  conversation_id: string;
  turn_index: number;
  role: Role;
  content: string;
  citations: Citation[] | null;
  cost_usd: number | null;
  latency_ms: number | null;
  created_at: string;
}

interface ConversationDetail extends ConversationSummary {
  turns: TurnDetail[];
}

interface AszfChatResponse {
  answer: string;
  citations: Citation[];
  cost_usd: number;
  latency_ms: number;
  persona: Persona;
  collection: string;
  hallucination_score: number | null;
}

interface RagCollectionListItem {
  id: string;
  name: string;
  tenant_id: string;
  document_count?: number;
}

interface RagCollectionListResponse {
  items: RagCollectionListItem[];
  total: number;
  source: string;
}

// Local-only stream marker so persona switches are operator-visible without
// taking up a row in aszf_conversation_turns.
interface PersonaChangeMarker {
  kind: "persona_change";
  id: string;
  from_persona: Persona;
  to_persona: Persona;
  at: string;
}

type StreamEntry = TurnDetail | PersonaChangeMarker;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const PERSONAS: Persona[] = ["baseline", "expert", "mentor"];

const PERSONA_BADGE_CLASS: Record<Persona, string> = {
  baseline:
    "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  expert:
    "bg-violet-50 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300",
  mentor:
    "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
};

function formatCost(cost: number | null | undefined): string {
  if (cost == null || cost === 0) return "$0";
  if (cost < 0.0001) return "<$0.0001";
  if (cost < 0.01) return `$${cost.toFixed(4)}`;
  return `$${cost.toFixed(2)}`;
}

function formatLatency(ms: number | null | undefined): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

function relativeTime(iso: string): string {
  try {
    const diff = Date.now() - new Date(iso).getTime();
    const m = Math.floor(diff / 60_000);
    if (m < 1) return "just now";
    if (m < 60) return `${m}m ago`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h}h ago`;
    const d = Math.floor(h / 24);
    return `${d}d ago`;
  } catch {
    return iso;
  }
}

function conversationLabel(c: ConversationSummary, firstUserSnippet?: string): string {
  if (c.title) return c.title;
  if (firstUserSnippet) {
    const s = firstUserSnippet.trim();
    return s.length > 60 ? `${s.slice(0, 60)}…` : s || "Új beszélgetés";
  }
  return "Új beszélgetés";
}

function downloadJson(filename: string, payload: unknown): void {
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------------------
// Page component
// ---------------------------------------------------------------------------

export function AszfChat() {
  const translate = useTranslate();
  const tenantId =
    typeof window !== "undefined"
      ? localStorage.getItem("aiflow_tenant") || "default"
      : "default";

  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [stream, setStream] = useState<StreamEntry[]>([]);
  const [persona, setPersona] = useState<Persona>("baseline");
  const [collection, setCollection] = useState<string>("");
  const [collections, setCollections] = useState<RagCollectionListItem[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [empty, setEmpty] = useState(false);
  const streamEndRef = useRef<HTMLDivElement | null>(null);

  // -------------------------------------------------------------------------
  // Initial load: collections + conversation list
  // -------------------------------------------------------------------------

  useEffect(() => {
    const ctl = new AbortController();
    fetchApi<RagCollectionListResponse>(
      "GET",
      `/api/v1/rag-collections?tenant_id=${encodeURIComponent(tenantId)}`,
      undefined,
      { signal: ctl.signal },
    )
      .then((res) => {
        setCollections(res.items);
        if (res.items.length > 0 && !collection) {
          setCollection(res.items[0].name);
        }
      })
      .catch((err) => {
        if (err instanceof ApiClientError) {
          setError(`${err.status}: ${err.message}`);
        }
      });
    return () => ctl.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId]);

  const refreshConversations = useCallback(async () => {
    try {
      const rows = await fetchApi<ConversationSummary[]>(
        "GET",
        `/api/v1/conversations/?tenant_id=${encodeURIComponent(tenantId)}&limit=50`,
      );
      setConversations(rows);
      setEmpty(rows.length === 0);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(`${err.status}: ${err.message}`);
      }
    }
  }, [tenantId]);

  useEffect(() => {
    refreshConversations();
  }, [refreshConversations]);

  // Auto-scroll to the latest turn whenever the stream changes.
  useEffect(() => {
    streamEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [stream.length]);

  // -------------------------------------------------------------------------
  // Conversation selection / loading
  // -------------------------------------------------------------------------

  const loadConversation = useCallback(
    async (conversationId: string) => {
      try {
        setError(null);
        const detail = await fetchApi<ConversationDetail>(
          "GET",
          `/api/v1/conversations/${conversationId}?tenant_id=${encodeURIComponent(tenantId)}`,
        );
        setSelectedId(detail.id);
        setPersona(detail.persona);
        setCollection(detail.collection_name);
        setStream(detail.turns);
      } catch (err) {
        if (err instanceof ApiClientError) {
          setError(`${err.status}: ${err.message}`);
        }
      }
    },
    [tenantId],
  );

  const startNewConversation = useCallback(() => {
    setSelectedId(null);
    setStream([]);
    setError(null);
  }, []);

  // -------------------------------------------------------------------------
  // Persona switch (mid-conversation marker)
  // -------------------------------------------------------------------------

  const switchPersona = useCallback(
    (next: Persona) => {
      if (next === persona) return;
      if (selectedId && stream.length > 0) {
        setStream((prev) => [
          ...prev,
          {
            kind: "persona_change",
            id: `marker-${Date.now()}`,
            from_persona: persona,
            to_persona: next,
            at: new Date().toISOString(),
          },
        ]);
      }
      setPersona(next);
    },
    [persona, selectedId, stream.length],
  );

  // -------------------------------------------------------------------------
  // Send a turn
  // -------------------------------------------------------------------------

  const sendTurn = useCallback(async () => {
    const question = input.trim();
    if (!question || busy) return;
    if (!collection) {
      setError("Válassz egy gyűjteményt mielőtt kérdést küldesz.");
      return;
    }
    setBusy(true);
    setError(null);

    try {
      // 1. Ensure a conversation row exists.
      let conversationId = selectedId;
      if (!conversationId) {
        const created = await fetchApi<ConversationSummary>(
          "POST",
          `/api/v1/conversations/?tenant_id=${encodeURIComponent(tenantId)}`,
          {
            persona,
            collection_name: collection,
            title: null,
          },
        );
        conversationId = created.id;
        setSelectedId(created.id);
      }

      // 2. Persist the user turn FIRST so it survives a mid-flight crash.
      const userTurn = await fetchApi<TurnDetail>(
        "POST",
        `/api/v1/conversations/${conversationId}/turns?tenant_id=${encodeURIComponent(tenantId)}`,
        {
          role: "user",
          content: question,
        },
      );
      setStream((prev) => [...prev, userTurn]);
      setInput("");

      // 3. Call the retrieval endpoint to get answer + citations.
      const conversationHistory = stream
        .filter((s): s is TurnDetail => "role" in s)
        .map((t) => ({ role: t.role, content: t.content }));
      const answer = await fetchApi<AszfChatResponse>(
        "POST",
        `/api/v1/aszf/chat?tenant_id=${encodeURIComponent(tenantId)}`,
        {
          question,
          collection,
          persona,
          language: "hu",
          top_k: 5,
          conversation_history: conversationHistory,
        },
      );

      // 4. Persist the assistant turn with citations + cost + latency.
      const assistantTurn = await fetchApi<TurnDetail>(
        "POST",
        `/api/v1/conversations/${conversationId}/turns?tenant_id=${encodeURIComponent(tenantId)}`,
        {
          role: "assistant",
          content: answer.answer,
          citations: answer.citations,
          cost_usd: answer.cost_usd,
          latency_ms: answer.latency_ms,
        },
      );
      setStream((prev) => [...prev, assistantTurn]);

      // 5. Refresh sidebar so the order reflects the new updated_at.
      refreshConversations();
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(`${err.status}: ${err.message}`);
      } else if (err instanceof Error) {
        setError(err.message);
      }
    } finally {
      setBusy(false);
    }
  }, [
    busy,
    collection,
    input,
    persona,
    refreshConversations,
    selectedId,
    stream,
    tenantId,
  ]);

  // -------------------------------------------------------------------------
  // Derived state
  // -------------------------------------------------------------------------

  const cumulativeCost = useMemo(() => {
    let total = 0;
    for (const e of stream) {
      if ("role" in e && e.role === "assistant" && e.cost_usd != null) {
        total += e.cost_usd;
      }
    }
    return total;
  }, [stream]);

  const firstUserSnippets = useMemo(() => {
    // Best-effort label fallback per conversation row — only the active
    // conversation has its first turn loaded, so other rows fall back to
    // the title (if set) or a generic placeholder.
    const map = new Map<string, string>();
    if (selectedId) {
      const firstUser = stream.find((s): s is TurnDetail => "role" in s && s.role === "user");
      if (firstUser) map.set(selectedId, firstUser.content);
    }
    return map;
  }, [selectedId, stream]);

  const exportTranscript = useCallback(() => {
    if (!selectedId) return;
    const conv = conversations.find((c) => c.id === selectedId);
    const payload = {
      conversation: conv,
      turns: stream.filter((s): s is TurnDetail => "role" in s),
      exported_at: new Date().toISOString(),
    };
    const filename = `aszf-chat-${selectedId.slice(0, 8)}.json`;
    downloadJson(filename, payload);
  }, [conversations, selectedId, stream]);

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <PageLayout
      titleKey="aiflow.aszfChat.title"
      subtitleKey="aiflow.aszfChat.subtitle"
    >
      <div className="grid grid-cols-12 gap-4 min-h-[600px]">
        {/* ----------------------------------------------------------------
            Left sidebar — conversation history
        ---------------------------------------------------------------- */}
        <aside className="col-span-3 border-r border-gray-200 dark:border-gray-700 pr-3 flex flex-col">
          <button
            type="button"
            onClick={startNewConversation}
            data-testid="aszf-new-conversation"
            className="mb-3 w-full rounded-md bg-violet-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-violet-700"
          >
            {translate("aiflow.aszfChat.newConversation")}
          </button>

          {empty && (
            <div
              data-testid="aszf-empty-state"
              className="rounded-md border border-dashed border-gray-300 dark:border-gray-700 p-3 text-sm text-gray-500 dark:text-gray-400"
            >
              {translate("aiflow.aszfChat.empty")}
            </div>
          )}

          <ul className="flex-1 space-y-1 overflow-y-auto">
            {conversations.map((c) => {
              const active = c.id === selectedId;
              return (
                <li key={c.id}>
                  <button
                    type="button"
                    onClick={() => loadConversation(c.id)}
                    data-testid={`aszf-conv-item-${c.id}`}
                    className={`w-full rounded-md px-3 py-2 text-left text-sm transition ${
                      active
                        ? "bg-violet-50 text-violet-900 dark:bg-violet-900/30 dark:text-violet-100"
                        : "hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate">
                        {conversationLabel(c, firstUserSnippets.get(c.id))}
                      </span>
                      <span
                        className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium ${PERSONA_BADGE_CLASS[c.persona]}`}
                      >
                        {c.persona}
                      </span>
                    </div>
                    <div className="mt-0.5 text-xs text-gray-500 dark:text-gray-500">
                      {relativeTime(c.updated_at)}
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        </aside>

        {/* ----------------------------------------------------------------
            Center column — top bar + turn stream + composer
        ---------------------------------------------------------------- */}
        <section className="col-span-9 flex flex-col">
          {/* Top bar */}
          <div className="flex flex-wrap items-center gap-3 border-b border-gray-200 dark:border-gray-700 pb-3 mb-3">
            <div className="inline-flex rounded-md border border-gray-200 dark:border-gray-700 overflow-hidden">
              {PERSONAS.map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => switchPersona(p)}
                  data-testid={`aszf-persona-${p}`}
                  aria-pressed={persona === p}
                  className={`px-3 py-1.5 text-sm transition ${
                    persona === p
                      ? "bg-violet-600 text-white"
                      : "bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>

            <select
              data-testid="aszf-collection-picker"
              value={collection}
              onChange={(e) => setCollection(e.target.value)}
              disabled={!!selectedId}
              className="rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-1.5 text-sm text-gray-700 dark:text-gray-300 disabled:opacity-50"
              aria-label={translate("aiflow.aszfChat.collection")}
            >
              {collections.length === 0 && <option value="">—</option>}
              {collections.map((c) => (
                <option key={c.id} value={c.name}>
                  {c.name}
                </option>
              ))}
            </select>

            <div
              data-testid="aszf-cost-meter"
              className="ml-auto inline-flex items-center gap-2 rounded-md bg-gray-50 dark:bg-gray-800 px-3 py-1.5 text-sm"
            >
              <span className="text-gray-500 dark:text-gray-400">
                {translate("aiflow.aszfChat.cumulativeCost")}
              </span>
              <span className="font-mono font-medium text-gray-900 dark:text-gray-100">
                {formatCost(cumulativeCost)}
              </span>
            </div>

            <button
              type="button"
              onClick={exportTranscript}
              disabled={!selectedId || stream.length === 0}
              data-testid="aszf-transcript-export"
              className="rounded-md border border-gray-200 dark:border-gray-700 px-3 py-1.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50"
            >
              {translate("aiflow.aszfChat.exportTranscript")}
            </button>
          </div>

          {error && (
            <div
              data-testid="aszf-error"
              className="mb-3 rounded-md bg-rose-50 dark:bg-rose-900/30 px-3 py-2 text-sm text-rose-700 dark:text-rose-300"
            >
              {error}
            </div>
          )}

          {/* Turn stream */}
          <div
            data-testid="aszf-turn-stream"
            className="flex-1 space-y-3 overflow-y-auto pr-1"
          >
            {stream.length === 0 && !busy && (
              <p className="rounded-md border border-dashed border-gray-300 dark:border-gray-700 p-6 text-center text-sm text-gray-500 dark:text-gray-400">
                {translate("aiflow.aszfChat.composerHint")}
              </p>
            )}
            {stream.map((entry) => {
              if ("kind" in entry && entry.kind === "persona_change") {
                return (
                  <div
                    key={entry.id}
                    data-testid="aszf-persona-change-marker"
                    className="flex items-center justify-center"
                  >
                    <div className="rounded-full bg-amber-50 dark:bg-amber-900/30 px-3 py-1 text-xs text-amber-700 dark:text-amber-300">
                      {translate("aiflow.aszfChat.personaChanged", {
                        from: entry.from_persona,
                        to: entry.to_persona,
                      })}
                    </div>
                  </div>
                );
              }
              const turn = entry as TurnDetail;
              const isUser = turn.role === "user";
              return (
                <div
                  key={turn.id}
                  data-testid={`aszf-turn-${turn.role}`}
                  className={`flex ${isUser ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[75%] rounded-lg px-4 py-3 text-sm ${
                      isUser
                        ? "bg-violet-600 text-white"
                        : "bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{turn.content}</div>
                    {!isUser && turn.citations && turn.citations.length > 0 && (
                      <div
                        data-testid="aszf-citation-card"
                        className="mt-3 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-2 text-xs"
                      >
                        <div className="mb-1 font-medium text-gray-700 dark:text-gray-300">
                          {translate("aiflow.aszfChat.citations")}
                        </div>
                        <ul className="space-y-1">
                          {turn.citations.map((c, i) => (
                            <li key={`${turn.id}-cit-${i}`} className="flex items-start gap-2">
                              <span className="mt-0.5 inline-block rounded bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 font-mono text-[10px] text-gray-700 dark:text-gray-300">
                                [{i + 1}]
                              </span>
                              <div className="flex-1">
                                <div className="font-medium text-gray-900 dark:text-gray-100">
                                  {c.title || c.source_id}
                                </div>
                                {c.snippet && (
                                  <div className="text-gray-500 dark:text-gray-400 line-clamp-2">
                                    {c.snippet}
                                  </div>
                                )}
                              </div>
                              {c.score != null && (
                                <span className="shrink-0 font-mono text-[10px] text-gray-500 dark:text-gray-500">
                                  {(c.score * 100).toFixed(0)}%
                                </span>
                              )}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {!isUser && (turn.cost_usd != null || turn.latency_ms != null) && (
                      <div className="mt-2 flex items-center gap-3 text-[10px] text-gray-500 dark:text-gray-500">
                        <span>{formatCost(turn.cost_usd)}</span>
                        <span>·</span>
                        <span>{formatLatency(turn.latency_ms)}</span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
            {busy && (
              <div
                data-testid="aszf-busy"
                className="flex justify-start text-sm italic text-gray-500 dark:text-gray-400"
              >
                {translate("aiflow.aszfChat.thinking")}
              </div>
            )}
            <div ref={streamEndRef} />
          </div>

          {/* Composer */}
          <form
            className="mt-3 flex items-center gap-2 border-t border-gray-200 dark:border-gray-700 pt-3"
            onSubmit={(e) => {
              e.preventDefault();
              sendTurn();
            }}
          >
            <input
              type="text"
              data-testid="aszf-composer-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={translate("aiflow.aszfChat.placeholder")}
              disabled={busy}
              className="flex-1 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100"
            />
            <button
              type="submit"
              disabled={busy || !input.trim() || !collection}
              data-testid="aszf-composer-send"
              className="rounded-md bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50"
            >
              {translate("aiflow.aszfChat.send")}
            </button>
          </form>
        </section>
      </div>
    </PageLayout>
  );
}
