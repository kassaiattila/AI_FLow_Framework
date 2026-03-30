"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

interface ChatInputProps {
  onSend: (question: string, role: string) => void;
  disabled?: boolean;
}

const ROLES = [
  { value: "baseline", label: "Alapszint" },
  { value: "mentor", label: "Mentor" },
  { value: "expert", label: "Szakerto" },
];

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [question, setQuestion] = useState("");
  const [role, setRole] = useState("baseline");

  const handleSend = () => {
    const q = question.trim();
    if (!q) return;
    onSend(q, role);
    setQuestion("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t p-3 space-y-2">
      <div className="flex items-center gap-2">
        <select
          value={role}
          onChange={(e) => setRole(e.target.value)}
          className="text-xs border rounded px-2 py-1 bg-background"
        >
          {ROLES.map((r) => (
            <option key={r.value} value={r.value}>
              {r.label}
            </option>
          ))}
        </select>
      </div>
      <div className="flex gap-2">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Kerdes..."
          className="flex-1 resize-none border rounded-lg px-3 py-2 text-sm min-h-[40px] max-h-[120px] bg-background"
          rows={1}
          disabled={disabled}
        />
        <Button
          onClick={handleSend}
          disabled={disabled || !question.trim()}
          size="sm"
          className="self-end"
        >
          Kuldes
        </Button>
      </div>
    </div>
  );
}
