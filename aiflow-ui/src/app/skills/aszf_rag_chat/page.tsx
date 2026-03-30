"use client";

import { useEffect, useState, useCallback } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ChatMessages } from "@/components/rag-chat/chat-messages";
import { ChatInput } from "@/components/rag-chat/chat-input";
import { CitationPanel } from "@/components/rag-chat/citation-panel";
import { SearchRelevance } from "@/components/rag-chat/search-relevance";
import { StepTrace } from "@/components/rag-chat/step-trace";
import { useI18n } from "@/hooks/use-i18n";
import type { RagConversation, RagMessage, QueryOutput } from "@/lib/types";

export default function AszfRagChatPage() {
  const { t } = useI18n();
  const [conversations, setConversations] = useState<RagConversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<RagMessage[]>([]);
  const [lastOutput, setLastOutput] = useState<QueryOutput | null>(null);
  const [activeCitation, setActiveCitation] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [pageLoading, setPageLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [source, setSource] = useState<"backend" | "demo" | null>(null);

  const loadConversations = useCallback(() => {
    setPageLoading(true);
    setError(null);
    fetch("/api/rag/conversations")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: { conversations: RagConversation[] }) => {
        setConversations(data.conversations);
        if (data.conversations.length > 0 && !activeConvId) {
          const first = data.conversations[0];
          setActiveConvId(first.conversation_id);
          setMessages(first.messages);
          const lastAssistant = [...first.messages]
            .reverse()
            .find((m) => m.role === "assistant" && m.query_output);
          if (lastAssistant?.query_output) {
            setLastOutput(lastAssistant.query_output);
          }
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setPageLoading(false));
  }, []);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  const handleConversationSelect = (conv: RagConversation) => {
    setActiveConvId(conv.conversation_id);
    setMessages(conv.messages);
    const lastAssistant = [...conv.messages]
      .reverse()
      .find((m) => m.role === "assistant" && m.query_output);
    setLastOutput(lastAssistant?.query_output || null);
    setActiveCitation(null);
  };

  const handleSend = async (question: string, role: string) => {
    const userMsg: RagMessage = { role: "user", content: question };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    setActiveCitation(null);

    // Add placeholder assistant message for streaming
    const thinkingMsg: RagMessage = { role: "assistant", content: `_${t("rag.thinking")}_` };
    setMessages((prev) => [...prev, thinkingMsg]);

    try {
      const res = await fetch("/api/rag/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, role }),
      });

      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let streamedContent = "";
      let finalOutput: QueryOutput | null = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6).trim();
          if (payload === "[DONE]") continue;

          try {
            const event = JSON.parse(payload);
            if (event.type === "source") {
              setSource(event.mode === "backend" ? "backend" : "demo");
            } else if (event.type === "token") {
              streamedContent += event.content;
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  role: "assistant",
                  content: streamedContent,
                };
                return updated;
              });
            } else if (event.type === "metadata") {
              finalOutput = {
                answer: streamedContent,
                citations: event.citations || [],
                search_results: event.search_results || [],
                hallucination_score: event.hallucination_score ?? 1,
                processing_time_ms: event.processing_time_ms ?? 0,
                tokens_used: event.tokens_used ?? 0,
                cost_usd: event.cost_usd ?? 0,
              };
            }
          } catch {
            // Skip malformed SSE lines
          }
        }
      }

      // Update final message with metadata
      if (finalOutput) {
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content: finalOutput!.answer,
            query_output: finalOutput!,
          };
          return updated;
        });
        setLastOutput(finalOutput);
      }
    } catch {
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          content: t("rag.queryError"),
        };
        return updated;
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 space-y-4 h-[calc(100vh-0px)]">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">{t("rag.title")}</h2>
          <p className="text-muted-foreground">
            {t("rag.desc")}
          </p>
        </div>
        {source === "demo" ? (
          <Badge className="bg-yellow-100 text-yellow-800 text-sm px-3 py-1">{t("backend.demo")}</Badge>
        ) : source === "backend" ? (
          <Badge className="bg-green-100 text-green-800 text-sm px-3 py-1">{t("backend.live")} — {t("rag.evalBadge")}</Badge>
        ) : (
          <Badge className="bg-gray-100 text-gray-600 text-sm px-3 py-1">{t("rag.evalBadge")}</Badge>
        )}
      </div>

      {pageLoading && (
        <Card><div className="py-12 text-center text-muted-foreground">{t("common.loading")}</div></Card>
      )}

      {error && (
        <Card><div className="py-8 text-center">
          <p className="text-red-600 text-sm mb-2">{t("common.errorPrefix")}{error}</p>
          <button onClick={loadConversations} className="text-sm text-blue-600 underline">{t("common.retry")}</button>
        </div></Card>
      )}

      {!pageLoading && !error && <>
      {/* Conversation selector */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {conversations.map((conv) => (
          <button
            key={conv.conversation_id}
            onClick={() => handleConversationSelect(conv)}
            className={`px-3 py-1 rounded-full text-xs whitespace-nowrap border transition-colors ${
              activeConvId === conv.conversation_id
                ? "bg-primary text-primary-foreground"
                : "hover:bg-muted"
            }`}
          >
            {conv.title}
          </button>
        ))}
      </div>

      {/* Main layout: chat + right panel */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 flex-1" style={{ height: "calc(100vh - 200px)" }}>
        {/* Left: Chat (3/5) */}
        <Card className="lg:col-span-3 flex flex-col overflow-hidden">
          <ChatMessages
            messages={messages}
            activeCitation={activeCitation}
            onCitationClick={setActiveCitation}
          />
          <ChatInput onSend={handleSend} disabled={loading} />
        </Card>

        {/* Right: Citations + Search + Trace (2/5) */}
        <div className="lg:col-span-2">
          <Tabs defaultValue="citations">
            <TabsList>
              <TabsTrigger value="citations">
                {t("rag.citations")}
                {lastOutput && lastOutput.citations.length > 0 && (
                  <Badge className="ml-1 bg-blue-100 text-blue-800 text-[9px]">
                    {lastOutput.citations.length}
                  </Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="search">{t("rag.search")}</TabsTrigger>
              <TabsTrigger value="trace">{t("rag.pipeline")}</TabsTrigger>
            </TabsList>

            <TabsContent value="citations" className="mt-3 max-h-[calc(100vh-300px)] overflow-y-auto">
              <CitationPanel
                citations={lastOutput?.citations || []}
                activeCitation={activeCitation}
              />
            </TabsContent>

            <TabsContent value="search" className="mt-3 max-h-[calc(100vh-300px)] overflow-y-auto">
              <SearchRelevance results={lastOutput?.search_results || []} />
            </TabsContent>

            <TabsContent value="trace" className="mt-3 max-h-[calc(100vh-300px)] overflow-y-auto">
              {lastOutput ? (
                <StepTrace queryOutput={lastOutput} source={source} isProcessing={loading} />
              ) : (
                <p className="text-sm text-muted-foreground text-center py-8">
                  {t("rag.noOutput")}
                </p>
              )}
            </TabsContent>
          </Tabs>
        </div>
      </div>
      </>}
    </div>
  );
}
