"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useI18n } from "@/hooks/use-i18n";

interface TextInputFormProps {
  onGenerate: (userInput: string) => void;
  disabled?: boolean;
}

export function TextInputForm({ onGenerate, disabled }: TextInputFormProps) {
  const { t } = useI18n();
  const [text, setText] = useState("");

  const handleGenerate = () => {
    const trimmed = text.trim();
    if (!trimmed) return;
    onGenerate(trimmed);
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm">{t("processdoc.formTitle")}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={t("processdoc.formPlaceholder")}
          className="w-full border rounded-lg px-3 py-2 text-sm min-h-[120px] resize-y bg-background"
          disabled={disabled}
        />
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">{text.length} {t("processdoc.charCount")}</span>
          <Button onClick={handleGenerate} disabled={disabled || !text.trim()} size="sm">
            {disabled ? t("processdoc.generating") : t("processdoc.generate")}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
