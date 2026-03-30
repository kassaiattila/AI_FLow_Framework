"use client";

import { Card, CardContent } from "@/components/ui/card";

interface LoadingStateProps {
  message?: string;
}

export function LoadingState({ message = "Betoltes..." }: LoadingStateProps) {
  return (
    <Card>
      <CardContent className="py-12 text-center space-y-3">
        <div className="w-48 mx-auto h-1.5 bg-muted rounded-full overflow-hidden">
          <div className="h-full w-1/3 bg-primary rounded-full animate-pulse" />
        </div>
        <p className="text-sm text-muted-foreground">{message}</p>
      </CardContent>
    </Card>
  );
}

interface ErrorStateProps {
  error: string;
  onRetry?: () => void;
}

export function ErrorState({ error, onRetry }: ErrorStateProps) {
  return (
    <Card>
      <CardContent className="py-8 text-center space-y-2">
        <p className="text-sm text-red-600">{error}</p>
        {onRetry && (
          <button onClick={onRetry} className="text-sm text-blue-600 underline hover:text-blue-800">
            Ujraprobalkozas
          </button>
        )}
      </CardContent>
    </Card>
  );
}

interface EmptyStateProps {
  message?: string;
}

export function EmptyState({ message = "Nincs adat" }: EmptyStateProps) {
  return (
    <Card>
      <CardContent className="py-12 text-center">
        <p className="text-sm text-muted-foreground">{message}</p>
      </CardContent>
    </Card>
  );
}
