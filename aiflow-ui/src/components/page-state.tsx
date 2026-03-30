"use client";

import { Card, CardContent } from "@/components/ui/card";
import { useI18n } from "@/hooks/use-i18n";

interface LoadingStateProps {
  message?: string;
}

export function LoadingState({ message }: LoadingStateProps) {
  const { t } = useI18n();
  return (
    <Card>
      <CardContent className="py-12 text-center space-y-3">
        <div className="w-48 mx-auto h-1.5 bg-muted rounded-full overflow-hidden">
          <div className="h-full w-1/3 bg-primary rounded-full animate-pulse" />
        </div>
        <p className="text-sm text-muted-foreground">{message || t("common.loading")}</p>
      </CardContent>
    </Card>
  );
}

interface ErrorStateProps {
  error: string;
  onRetry?: () => void;
}

export function ErrorState({ error, onRetry }: ErrorStateProps) {
  const { t } = useI18n();
  return (
    <Card>
      <CardContent className="py-8 text-center space-y-2">
        <p className="text-sm text-red-600">{error}</p>
        {onRetry && (
          <button onClick={onRetry} className="text-sm text-blue-600 underline hover:text-blue-800">
            {t("common.retryBtn")}
          </button>
        )}
      </CardContent>
    </Card>
  );
}

interface EmptyStateProps {
  message?: string;
}

export function EmptyState({ message }: EmptyStateProps) {
  const { t } = useI18n();
  return (
    <Card>
      <CardContent className="py-12 text-center">
        <p className="text-sm text-muted-foreground">{message || t("common.noData")}</p>
      </CardContent>
    </Card>
  );
}
