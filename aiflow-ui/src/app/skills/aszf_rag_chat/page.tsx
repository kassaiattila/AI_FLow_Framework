"use client";

import { useEffect, useState, useCallback } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ChatMessages } from "@/components/rag-chat/chat-messages";
import { ChatInput } from "@/components/rag-chat/chat-input";
import { CitationPanel } from "@/components/rag-chat/citation-panel";
import { SearchRelevance } from "@/components/rag-chat/search-relevance";
import { SkillViewerLayout, PipelineBar } from "@/components/skill-viewer";
import { useI18n } from "@/hooks/use-i18n";
import type { RagConversation, RagMessage, QueryOutput } from "@/lib/types";

const RAG_PIPELINE = ["rewrite", "search", "context", "generate", "citations", "hallucination"];

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
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then((data: { conversations: RagConversation[] }) => {
        setConversations(data.conversations);
        if (data.conversations.length > 0 && !activeConvId) {
          const first = data.conversations[0];
          setActiveConvId(first.conversation_id);
          setMessages(first.messages);
          const lastAssistant = [...first.messages].reverse().find((m) => m.role === "assistant" && m.query_output);
          if (lastAssistant?.query_output) setLastOutput(lastAssistant.query_output);
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setPageLoading(false));
  }, []);

  useEffect(() => { loadConversations(); }, [loadConversations]);

  const handleConversationSelect = (conv: RagConversation) => {
    setActiveConvId(conv.conversation_id);
    setMessages(conv.messages);
    const lastAssistant = [...conv.messages].reverse().find((m) => m.role === "assistant" && m.query_output);
    setLastOutput(lastAssistant?.query_output || null);
    setActiveCitation(null);
  };

  const handleSend = async (question: string, role: string) => {
    const userMsg: RagMessage = { role: "user", content: question };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    setActiveCitation(null);
    setMessages((prev) => [...prev, { role: "assistant", content: `_${t("rag.thinking")}_` }]);

    try {
      const res = await fetch("/api/rag/stream", {
        method: "POST", headers: { "Content-Type": "application/json" },
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
        for (const line of chunk.split("\n")) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6).trim();
          if (payload === "[DONE]") continue;
          try {
            const event = JSON.parse(payload);
            if (event.type === "source") setSource(event.mode === "backend" ? "backend" : "demo");
            else if (event.type === "token") {
              streamedContent += event.content;
              setMessages((prev) => { const u = [...prev]; u[u.length - 1] = { role: "assistant", content: streamedContent }; return u; });
            } else if (event.type === "metadata") {
              finalOutput = { answer: streamedContent, citations: event.citations || [], search_results: event.search_results || [], hallucination_score: event.hallucination_score ?? 1, processing_time_ms: event.processing_time_ms ?? 0, tokens_used: event.tokens_used ?? 0, cost_usd: event.cost_usd ?? 0 };
            }
          } catch { /* skip */ }
        }
      }

      if (finalOutput) {
        setMessages((prev) => { const u = [...prev]; u[u.length - 1] = { role: "assistant", content: finalOutput!.answer, query_output: finalOutput! }; return u; });
        setLastOutput(finalOutput);
      }
    } catch {
      setMessages((prev) => { const u = [...prev]; u[u.length - 1] = { role: "assistant", content: t("rag.queryError") }; return u; });
    } finally {
      setLoading(false);
    }
  };

  // Pipeline steps based on query output
  const pipelineSteps = RAG_PIPELINE.map((name) => ({
    name,
    status: (lastOutput ? "completed" : "pending") as "completed" | "pending",
  }));

  return (
    <SkillViewerLayout
      skillName="rag"
      source={source}
      loading={pageLoading}
      error={error}
      onRetry={loadConversations}
      badgeExtra={source === "backend" ? t("rag.evalBadge") : undefined}
      badgeFallbackKey="rag.evalBadge"
      fullHeight
    >
      {/* 1. Conversation selector */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {conversations.map((conv) => (
          <button key={conv.conversation_id} onClick={() => handleConversationSelect(conv)}
            className={`px-3 py-1 rounded-full text-xs whitespace-nowrap border transition-colors ${activeConvId === conv.conversation_id ? "bg-primary text-primary-foreground" : "hover:bg-muted"}`}>
            {conv.title}
          </button>
        ))}
      </div>

      {/* 2. Pipeline bar — always visible */}
      <PipelineBar steps={pipelineSteps} source={source} isProcessing={loading} />

      {/* 3. Chat + sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 flex-1" style={{ height: "calc(100vh - 240px)" }}>
        <Card className="lg:col-span-3 flex flex-col overflow-hidden">
          <ChatMessages messages={messages} activeCitation={activeCitation} onCitationClick={setActiveCitation} />
          <ChatInput onSend={handleSend} disabled={loading} />
        </Card>
        <div className="lg:col-span-2">
          <Tabs defaultValue="citations">
            <TabsList>
              <TabsTrigger value="citations">
                {t("rag.citations")}
                {lastOutput && lastOutput.citations.length > 0 && (
                  <Badge className="ml-1 bg-blue-100 text-blue-800 text-[9px]">{lastOutput.citations.length}</Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="search">{t("rag.search")}</TabsTrigger>
            </TabsList>
            <TabsContent value="citations" className="mt-3 max-h-[calc(100vh-340px)] overflow-y-auto">
              <CitationPanel citations={lastOutput?.citations || []} activeCitation={activeCitation} />
            </TabsContent>
            <TabsContent value="search" className="mt-3 max-h-[calc(100vh-340px)] overflow-y-auto">
              <SearchRelevance results={lastOutput?.search_results || []} />
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </SkillViewerLayout>
  );
}
