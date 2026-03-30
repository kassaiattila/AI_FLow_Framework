"use client";

import type { ReactNode } from "react";
import { useI18n } from "@/hooks/use-i18n";
import { LoadingState, ErrorState } from "@/components/page-state";
import { SourceBadge } from "./source-badge";

type Source = "backend" | "subprocess" | "demo" | "filesystem" | null;

interface SkillViewerLayoutProps {
  skillName: string;
  source: Source;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  children: ReactNode;
  title?: string;
  description?: string;
  badgeExtra?: string;
  badgeFallbackKey?: string;
  headerActions?: ReactNode;
  headerNote?: string;
  fullHeight?: boolean;
}

export function SkillViewerLayout({
  skillName,
  source,
  loading,
  error,
  onRetry,
  children,
  title,
  description,
  badgeExtra,
  badgeFallbackKey,
  headerActions,
  headerNote,
  fullHeight = false,
}: SkillViewerLayoutProps) {
  const { t } = useI18n();

  const resolvedTitle = title || t(`${skillName}.title`);
  const resolvedDesc = description || t(`${skillName}.desc`);

  return (
    <div className={`p-6 ${fullHeight ? "space-y-4 h-[calc(100vh-0px)]" : "space-y-6"}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">{resolvedTitle}</h2>
          <p className="text-muted-foreground">{resolvedDesc}</p>
        </div>
        <div className="flex items-center gap-2">
          {headerActions}
          <SourceBadge source={source} extra={badgeExtra} fallbackKey={badgeFallbackKey} />
        </div>
      </div>

      {/* Optional hint below header */}
      {headerNote && (
        <p className="text-xs text-muted-foreground italic">{headerNote}</p>
      )}

      {/* Content: loading → error → children */}
      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState error={`${t("common.errorPrefix")}${error}`} onRetry={onRetry} />
      ) : (
        children
      )}
    </div>
  );
}
