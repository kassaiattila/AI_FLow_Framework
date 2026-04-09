/**
 * AIFlow Breadcrumb — route-based hierarchy display.
 * B8.2: "Dashboard > Group > Page" context indicator.
 */

import { Link, useLocation } from "react-router-dom";
import { useTranslate } from "../lib/i18n";

interface BreadcrumbSegment {
  label: string;
  path?: string;
}

/** Maps route paths to [group, page] breadcrumb segments using i18n keys */
const BREADCRUMB_MAP: Record<string, { groupKey: string; pageKey: string }> = {
  // Document Processing
  "/documents": { groupKey: "aiflow.menu.documentProcessing", pageKey: "aiflow.menu.documents" },
  "/emails": { groupKey: "aiflow.menu.documentProcessing", pageKey: "aiflow.menu.emailScan" },
  "/reviews": { groupKey: "aiflow.menu.documentProcessing", pageKey: "aiflow.menu.verification" },
  // Knowledge Base
  "/rag": { groupKey: "aiflow.menu.knowledgeBase", pageKey: "aiflow.menu.collections" },
  // Generation
  "/process-docs": { groupKey: "aiflow.menu.generation", pageKey: "aiflow.menu.diagrams" },
  "/spec-writer": { groupKey: "aiflow.menu.generation", pageKey: "aiflow.menu.specWriter" },
  "/media": { groupKey: "aiflow.menu.generation", pageKey: "aiflow.menu.mediaProcessing" },
  // Monitoring
  "/runs": { groupKey: "aiflow.menu.monitoring", pageKey: "aiflow.menu.pipelineRuns" },
  "/costs": { groupKey: "aiflow.menu.monitoring", pageKey: "aiflow.menu.costs" },
  "/monitoring": { groupKey: "aiflow.menu.monitoring", pageKey: "aiflow.menu.serviceHealth" },
  "/quality": { groupKey: "aiflow.menu.monitoring", pageKey: "aiflow.menu.llmQuality" },
  "/audit": { groupKey: "aiflow.menu.monitoring", pageKey: "aiflow.menu.auditLog" },
  // Settings
  "/admin": { groupKey: "aiflow.menu.settings", pageKey: "aiflow.menu.usersApi" },
  "/pipelines": { groupKey: "aiflow.menu.settings", pageKey: "aiflow.menu.pipelineTemplates" },
  "/services": { groupKey: "aiflow.menu.settings", pageKey: "aiflow.menu.serviceCatalog" },
  // More
  "/rpa": { groupKey: "aiflow.menu.more", pageKey: "aiflow.menu.rpaBrowser" },
  "/cubix": { groupKey: "aiflow.menu.more", pageKey: "aiflow.menu.cubixCourse" },
};

/** Group label → first route in that group (for clickable breadcrumb) */
const GROUP_ROUTES: Record<string, string> = {
  "aiflow.menu.documentProcessing": "/documents",
  "aiflow.menu.knowledgeBase": "/rag",
  "aiflow.menu.generation": "/process-docs",
  "aiflow.menu.monitoring": "/runs",
  "aiflow.menu.settings": "/admin",
  "aiflow.menu.more": "/rpa",
};

export function Breadcrumb() {
  const location = useLocation();
  const translate = useTranslate();
  const pathname = location.pathname;

  // Dashboard root — no breadcrumb needed
  if (pathname === "/" || pathname === "") return null;

  const segments: BreadcrumbSegment[] = [
    { label: "Dashboard", path: "/" },
  ];

  // Find matching route — try exact match first, then prefix match for detail routes
  const basePath = Object.keys(BREADCRUMB_MAP).find(
    (key) => pathname === key || pathname.startsWith(key + "/"),
  );

  if (basePath) {
    const mapping = BREADCRUMB_MAP[basePath];
    const groupRoute = GROUP_ROUTES[mapping.groupKey];
    segments.push({
      label: translate(mapping.groupKey),
      path: groupRoute,
    });

    if (pathname === basePath) {
      // Leaf page — not clickable
      segments.push({ label: translate(mapping.pageKey) });
    } else {
      // Detail page — make the page name clickable, add detail segment
      segments.push({
        label: translate(mapping.pageKey),
        path: basePath,
      });
      // Extract last meaningful segment for detail label
      const parts = pathname.replace(basePath + "/", "").split("/");
      const detailLabel = parts[parts.length - 1];
      // Capitalize common suffixes
      const DETAIL_LABELS: Record<string, string> = {
        show: translate("common.action.show"),
        verify: translate("aiflow.verification.verify"),
      };
      segments.push({
        label: DETAIL_LABELS[detailLabel] || decodeURIComponent(detailLabel),
      });
    }
  }

  // Don't show breadcrumb if we only have Dashboard
  if (segments.length <= 1) return null;

  return (
    <nav aria-label="Breadcrumb" className="mb-4 flex items-center gap-1 text-xs">
      {segments.map((seg, i) => {
        const isLast = i === segments.length - 1;
        return (
          <span key={i} className="flex items-center gap-1">
            {i > 0 && (
              <span className="text-gray-400 dark:text-gray-500">/</span>
            )}
            {isLast || !seg.path ? (
              <span className="text-gray-500 dark:text-gray-400">{seg.label}</span>
            ) : (
              <Link
                to={seg.path}
                className="text-gray-500 hover:text-brand-600 dark:text-gray-400 dark:hover:text-brand-400"
              >
                {seg.label}
              </Link>
            )}
          </span>
        );
      })}
    </nav>
  );
}
