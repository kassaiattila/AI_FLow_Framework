/**
 * AIFlow PageLayout — standard page wrapper with title, subtitle, source badge, actions.
 * Every page should use this for consistent layout.
 */

import type { ReactNode } from "react";
import { useTranslate } from "../lib/i18n";
import { StatusBadge } from "../components-new/StatusBadge";

interface PageLayoutProps {
  titleKey: string;
  subtitleKey?: string;
  source?: string | null;
  actions?: ReactNode;
  children: ReactNode;
}

export function PageLayout({
  titleKey,
  subtitleKey,
  source,
  actions,
  children,
}: PageLayoutProps) {
  const translate = useTranslate();

  return (
    <div className="mx-auto max-w-7xl">
      {/* Header */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-gray-900 dark:text-gray-100">
            {translate(titleKey)}
          </h1>
          {subtitleKey && (
            <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">
              {translate(subtitleKey)}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {source && <StatusBadge source={source} />}
          {actions}
        </div>
      </div>

      {/* Content */}
      {children}
    </div>
  );
}
