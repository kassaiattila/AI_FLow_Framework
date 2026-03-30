"use client";

import { useRef, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import type { RagMessage } from "@/lib/types";
import { HallucinationIndicator } from "./hallucination-indicator";

interface ChatMessagesProps {
  messages: RagMessage[];
  activeCitation: number | null;
  onCitationClick: (index: number) => void;
}

function renderContent(
  content: string,
  onCitationClick: (index: number) => void,
  activeCitation: number | null
): React.ReactNode[] {
  // Replace [1], [2] etc with clickable badges
  const parts: React.ReactNode[] = [];
  const regex = /\[(\d+)\]/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push(content.slice(lastIndex, match.index));
    }
    const citIndex = parseInt(match[1], 10);
    parts.push(
      <Badge
        key={`cit-${match.index}`}
        className={`cursor-pointer text-[10px] mx-0.5 ${
          activeCitation === citIndex
            ? "bg-blue-600 text-white"
            : "bg-blue-100 text-blue-800 hover:bg-blue-200"
        }`}
        onClick={() => onCitationClick(citIndex)}
      >
        {citIndex}
      </Badge>
    );
    lastIndex = regex.lastIndex;
  }

  if (lastIndex < content.length) {
    parts.push(content.slice(lastIndex));
  }

  return parts;
}

export function ChatMessages({ messages, activeCitation, onCitationClick }: ChatMessagesProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  return (
    <div className="flex-1 overflow-y-auto space-y-4 p-4">
      {messages.map((msg, idx) => (
        <div
          key={idx}
          className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
        >
          <div
            className={`max-w-[85%] rounded-lg px-4 py-3 text-sm ${
              msg.role === "user"
                ? "bg-blue-600 text-white"
                : "bg-muted"
            }`}
          >
            {msg.role === "assistant" ? (
              <>
                <div className="whitespace-pre-wrap leading-relaxed">
                  {renderContent(msg.content, onCitationClick, activeCitation)}
                </div>
                {msg.query_output && (
                  <div className="mt-2 pt-2 border-t border-border/50 flex items-center gap-3 text-xs">
                    <HallucinationIndicator score={msg.query_output.hallucination_score} />
                    <span className="text-muted-foreground">
                      {msg.query_output.processing_time_ms.toFixed(0)} ms
                    </span>
                    <span className="text-muted-foreground">
                      {msg.query_output.tokens_used} tok
                    </span>
                  </div>
                )}
              </>
            ) : (
              <p className="whitespace-pre-wrap">{msg.content}</p>
            )}
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
