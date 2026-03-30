"use client";

import { Button } from "@/components/ui/button";

interface PrintButtonProps {
  label?: string;
}

export function PrintButton({ label = "PDF / Print" }: PrintButtonProps) {
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() => window.print()}
      className="no-print"
    >
      {label}
    </Button>
  );
}
