import { useState, useRef, useEffect, useCallback } from "react";
import { useTranslate, Title, useNotify } from "react-admin";
import { useSearchParams } from "react-router-dom";
import {
  Card, CardContent, TextField, IconButton, Typography,
  CircularProgress, Alert, Chip, Box, Paper, Stack,
  MenuItem, ToggleButtonGroup, ToggleButton,
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import ThumbUpIcon from "@mui/icons-material/ThumbUp";
import ThumbUpOutlinedIcon from "@mui/icons-material/ThumbUpOutlined";
import ThumbDownIcon from "@mui/icons-material/ThumbDown";
import ThumbDownOutlinedIcon from "@mui/icons-material/ThumbDownOutlined";

const PRESET_QUESTIONS = [
  { key: "aszf", text: "Mi az ASZF es mire vonatkozik?" },
  { key: "rights", text: "Milyen jogaim vannak fogyasztokent?" },
  { key: "cancel", text: "Hogyan mondhatok fel egy szerzodest?" },
];

interface SimpleCollection {
  id: string;
  name: string;
}

type Role = "baseline" | "mentor" | "expert";

type RagStage = "embed" | "search" | "generate" | "hallucination" | "done";

const RAG_STAGES: { key: RagStage; label: string }[] = [
  { key: "embed", label: "Embed" },
  { key: "search", label: "Search" },
  { key: "generate", label: "Generate" },
  { key: "hallucination", label: "Halluc. check" },
];

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  metadata?: {
    citations?: unknown[];
    hallucination_score?: number;
    processing_time_ms?: number;
    tokens_used?: number;
    cost_usd?: number;
  };
}

export const RagChat = () => {
  const translate = useTranslate();
  const notify = useNotify();
  const [searchParams] = useSearchParams();
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [source, setSource] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ragStage, setRagStage] = useState<RagStage | null>(null);
  const [collections, setCollections] = useState<SimpleCollection[]>([]);
  const [selectedCollection, setSelectedCollection] = useState<string>(searchParams.get("collection") || "");
  const [role, setRole] = useState<Role>("mentor");
  const [feedback, setFeedback] = useState<Record<number, "up" | "down">>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Load collections for selector
  useEffect(() => {
    fetch("/api/v1/rag/collections")
      .then((r) => r.ok ? r.json() : { collections: [] })
      .then((data) => {
        const cols = (data.collections || []).map((c: { id: string; name: string }) => ({ id: c.id, name: c.name }));
        setCollections(cols);
        if (!selectedCollection && cols.length > 0) setSelectedCollection(cols[0].id);
      })
      .catch(() => {});
  }, []);// eslint-disable-line react-hooks/exhaustive-deps

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(scrollToBottom, [messages, scrollToBottom]);

  const handleFeedback = async (msgIndex: number, thumbsUp: boolean) => {
    if (!selectedCollection) return;
    setFeedback((prev) => ({ ...prev, [msgIndex]: thumbsUp ? "up" : "down" }));
    try {
      await fetch(`/api/v1/rag/collections/${selectedCollection}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query_id: `msg-${msgIndex}`, thumbs_up: thumbsUp }),
      });
    } catch {
      notify("Feedback failed", { type: "error" });
    }
  };

  const handleSend = async () => {
    const question = input.trim();
    if (!question || streaming) return;

    setInput("");
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setStreaming(true);
    setRagStage("embed");

    const controller = new AbortController();
    abortRef.current = controller;

    // Use collection-specific endpoint if available, fallback to legacy
    const endpoint = selectedCollection
      ? `/api/v1/rag/collections/${selectedCollection}/query`
      : "/api/v1/chat/completions";

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, role }),
        signal: controller.signal,
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      if (!res.body) throw new Error("No response body");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let assistantContent = "";
      let metadata: ChatMessage["metadata"] = undefined;
      let buffer = "";

      // Add empty assistant message
      setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6).trim();
          if (payload === "[DONE]") continue;

          try {
            const event = JSON.parse(payload);
            if (event.type === "source") {
              setSource(event.mode);
              setRagStage("search");
            } else if (event.type === "token") {
              if (ragStage !== "generate") setRagStage("generate");
              assistantContent += event.content;
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = { role: "assistant", content: assistantContent };
                return updated;
              });
            } else if (event.type === "metadata") {
              metadata = event;
              setRagStage("done");
            }
          } catch {
            // skip malformed JSON
          }
        }
      }

      // Final update with metadata
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = { role: "assistant", content: assistantContent, metadata };
        return updated;
      });
    } catch (e) {
      if ((e as Error).name !== "AbortError") {
        setError(e instanceof Error ? e.message : "Unknown error");
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Box sx={{ p: 3, maxWidth: 1000, mx: "auto", display: "flex", flexDirection: "column", height: "calc(100vh - 100px)" }}>
      <Title title={translate("aiflow.ragChat.title")} />

      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h6">{translate("aiflow.ragChat.title")}</Typography>
        {source && (
          <Chip
            label={translate(`aiflow.status.${source}`)}
            color={source === "demo" ? "warning" : "success"}
            size="small"
          />
        )}
      </Stack>

      {/* Collection + Role selectors */}
      <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }}>
        <TextField
          select
          size="small"
          label={translate("aiflow.ragChat.collection")}
          value={selectedCollection}
          onChange={(e) => setSelectedCollection(e.target.value)}
          sx={{ minWidth: 250 }}
        >
          {collections.map((c) => (
            <MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>
          ))}
          {collections.length === 0 && <MenuItem disabled>{translate("aiflow.rag.noCollections")}</MenuItem>}
        </TextField>
        <ToggleButtonGroup
          value={role}
          exclusive
          onChange={(_, v) => v && setRole(v as Role)}
          size="small"
        >
          <ToggleButton value="baseline">Baseline</ToggleButton>
          <ToggleButton value="mentor">Mentor</ToggleButton>
          <ToggleButton value="expert">Expert</ToggleButton>
        </ToggleButtonGroup>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 1 }}>{error}</Alert>}

      {/* Messages */}
      <Paper sx={{ flex: 1, overflow: "auto", p: 2, mb: 2, bgcolor: "background.default" }}>
        {messages.length === 0 && (
          <Box sx={{ textAlign: "center", mt: 4 }}>
            <Typography color="text.secondary" mb={2}>
              {translate("aiflow.ragChat.empty")}
            </Typography>
            {/* Preset questions (Pattern #4) */}
            <Stack direction="row" spacing={1} justifyContent="center" flexWrap="wrap" useFlexGap>
              {PRESET_QUESTIONS.map((q) => (
                <Chip
                  key={q.key}
                  label={q.text}
                  variant="outlined"
                  onClick={() => { setInput(q.text); }}
                  sx={{ cursor: "pointer" }}
                />
              ))}
            </Stack>
          </Box>
        )}
        {messages.map((msg, i) => (
          <Box key={i} sx={{ mb: 2, display: "flex", justifyContent: msg.role === "user" ? "flex-end" : "flex-start" }}>
            <Paper
              elevation={1}
              sx={{
                p: 1.5,
                maxWidth: "80%",
                bgcolor: msg.role === "user" ? "primary.dark" : "background.paper",
                borderRadius: 2,
              }}
            >
              <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
                {msg.content || (streaming && i === messages.length - 1 ? "..." : "")}
              </Typography>
              {/* Feedback buttons — wired to API */}
              {msg.role === "assistant" && msg.content && !streaming && (
                <Stack direction="row" spacing={0.5} sx={{ mt: 0.5 }}>
                  <IconButton size="small" onClick={() => handleFeedback(i, true)} color={feedback[i] === "up" ? "primary" : "default"} sx={{ opacity: feedback[i] === "up" ? 1 : 0.5, "&:hover": { opacity: 1 } }}>
                    {feedback[i] === "up" ? <ThumbUpIcon sx={{ fontSize: 14 }} /> : <ThumbUpOutlinedIcon sx={{ fontSize: 14 }} />}
                  </IconButton>
                  <IconButton size="small" onClick={() => handleFeedback(i, false)} color={feedback[i] === "down" ? "error" : "default"} sx={{ opacity: feedback[i] === "down" ? 1 : 0.5, "&:hover": { opacity: 1 } }}>
                    {feedback[i] === "down" ? <ThumbDownIcon sx={{ fontSize: 14 }} /> : <ThumbDownOutlinedIcon sx={{ fontSize: 14 }} />}
                  </IconButton>
                </Stack>
              )}
              {msg.metadata && (
                <Stack direction="row" spacing={0.5} sx={{ mt: 1 }} flexWrap="wrap" useFlexGap>
                  {msg.metadata.processing_time_ms != null && (
                    <Chip label={`${msg.metadata.processing_time_ms}ms`} size="small" variant="outlined" />
                  )}
                  {msg.metadata.tokens_used != null && (
                    <Chip label={`${msg.metadata.tokens_used} tokens`} size="small" variant="outlined" />
                  )}
                  {msg.metadata.cost_usd != null && (
                    <Chip label={`$${msg.metadata.cost_usd.toFixed(4)}`} size="small" variant="outlined" />
                  )}
                  {msg.metadata.hallucination_score != null && (
                    <Chip
                      label={`Halluc: ${(msg.metadata.hallucination_score * 100).toFixed(0)}%`}
                      size="small"
                      color={msg.metadata.hallucination_score > 0.3 ? "warning" : "success"}
                      variant="outlined"
                    />
                  )}
                </Stack>
              )}
            </Paper>
          </Box>
        ))}
        <div ref={messagesEndRef} />
      </Paper>

      {/* RAG Pipeline stages */}
      {streaming && ragStage && (
        <Stack direction="row" spacing={0.5} alignItems="center" sx={{ mb: 1 }}>
          {RAG_STAGES.map((stage, i) => {
            const stageIndex = RAG_STAGES.findIndex((s) => s.key === ragStage);
            const isDone = ragStage === "done" || i < stageIndex;
            const isActive = ragStage !== "done" && i === stageIndex;
            return (
              <Box key={stage.key} sx={{ display: "flex", alignItems: "center" }}>
                <Chip
                  label={stage.label}
                  size="small"
                  color={isDone ? "success" : isActive ? "primary" : "default"}
                  variant={isDone || isActive ? "filled" : "outlined"}
                  sx={{ fontSize: "0.7rem", height: 22, opacity: !isDone && !isActive ? 0.4 : 1 }}
                />
                {i < RAG_STAGES.length - 1 && (
                  <Typography variant="caption" sx={{ mx: 0.5, color: isDone ? "success.main" : "text.disabled" }}>
                    →
                  </Typography>
                )}
              </Box>
            );
          })}
        </Stack>
      )}

      {/* Input */}
      <Card>
        <CardContent sx={{ display: "flex", gap: 1, py: 1, "&:last-child": { pb: 1 } }}>
          <TextField
            fullWidth
            size="small"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={translate("aiflow.ragChat.placeholder")}
            disabled={streaming}
            multiline
            maxRows={3}
          />
          <IconButton onClick={handleSend} disabled={streaming || !input.trim()} color="primary">
            {streaming ? <CircularProgress size={24} /> : <SendIcon />}
          </IconButton>
        </CardContent>
      </Card>
    </Box>
  );
};
