"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/hooks/use-i18n";

interface ChatInputProps {
  onSend: (question: string, role: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const { t } = useI18n();
  const [question, setQuestion] = useState("");
  const [role, setRole] = useState("baseline");

  const ROLES = [
    { value: "baseline", label: t("rag.roleBaseline"), tip: t("rag.roleBaselineTip") },
    { value: "mentor", label: t("rag.roleMentor"), tip: t("rag.roleMentorTip") },
    { value: "expert", label: t("rag.roleExpert"), tip: t("rag.roleExpertTip") },
  ];

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
          title={ROLES.find((r) => r.value === role)?.tip}
        >
          {ROLES.map((r) => (
            <option key={r.value} value={r.value} title={r.tip}>
              {r.label}
            </option>
          ))}
        </select>
        <span className="text-[10px] text-muted-foreground">
          {ROLES.find((r) => r.value === role)?.tip}
        </span>
      </div>
      <div className="flex gap-2">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={t("rag.placeholder")}
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
          {t("common.send")}
        </Button>
      </div>
    </div>
  );
}
