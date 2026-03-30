"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface TextInputFormProps {
  onGenerate: (userInput: string) => void;
  disabled?: boolean;
}

export function TextInputForm({ onGenerate, disabled }: TextInputFormProps) {
  const [text, setText] = useState("");

  const handleGenerate = () => {
    const t = text.trim();
    if (!t) return;
    onGenerate(t);
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm">Folyamat leiras</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Irja le a folyamatot termeszetes nyelven... Pl: 'A penziugyi osztaly fogadja a szamlakat, ellenorzi a helyesseget, majd jovahagyja es kifizeti.'"
          className="w-full border rounded-lg px-3 py-2 text-sm min-h-[120px] resize-y bg-background"
          disabled={disabled}
        />
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">{text.length} karakter</span>
          <Button onClick={handleGenerate} disabled={disabled || !text.trim()} size="sm">
            {disabled ? "Generalas..." : "Diagram generalas"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
