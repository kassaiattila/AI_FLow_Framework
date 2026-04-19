/**
 * AIFlow Sidebar — Sprint C restructured groups.
 * C0.3: documentProcessing, knowledgeBase, pipelineAndRuns, monitoring, admin, archive.
 */

import { useState, useEffect } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useTranslate } from "../lib/i18n";

interface MenuItem {
  path: string;
  labelKey: string;
  icon: string;
}

interface MenuGroup {
  labelKey: string;
  defaultOpen: boolean;
  items: MenuItem[];
  archive?: boolean;
}

const MENU_GROUPS: MenuGroup[] = [
  {
    labelKey: "aiflow.menu.documentProcessing",
    defaultOpen: true,
    items: [
      { path: "/documents", labelKey: "aiflow.menu.documents", icon: "file-text" },
      { path: "/emails", labelKey: "aiflow.menu.emailScan", icon: "mail" },
      { path: "/reviews", labelKey: "aiflow.menu.reviewQueue", icon: "check-circle" },
    ],
  },
  {
    labelKey: "aiflow.menu.knowledgeBase",
    defaultOpen: false,
    items: [
      { path: "/rag", labelKey: "aiflow.menu.collections", icon: "book-open" },
    ],
  },
  {
    labelKey: "aiflow.menu.pipelineAndRuns",
    defaultOpen: true,
    items: [
      { path: "/runs", labelKey: "aiflow.menu.pipelineRuns", icon: "play-circle" },
      { path: "/pipelines", labelKey: "aiflow.menu.pipelineTemplates", icon: "layers" },
      { path: "/services", labelKey: "aiflow.menu.serviceCatalog", icon: "server" },
    ],
  },
  {
    labelKey: "aiflow.menu.monitoring",
    defaultOpen: false,
    items: [
      { path: "/costs", labelKey: "aiflow.menu.costs", icon: "trending-up" },
      { path: "/monitoring", labelKey: "aiflow.menu.serviceHealth", icon: "activity" },
      { path: "/quality", labelKey: "aiflow.menu.llmQuality", icon: "bar-chart" },
    ],
  },
  {
    labelKey: "aiflow.menu.settings",
    defaultOpen: false,
    items: [
      { path: "/admin", labelKey: "aiflow.menu.usersApi", icon: "users" },
      { path: "/audit", labelKey: "aiflow.menu.auditLog", icon: "clock" },
    ],
  },
  {
    labelKey: "aiflow.menu.archive",
    defaultOpen: true,
    archive: true,
    items: [
      { path: "/process-docs", labelKey: "aiflow.menu.diagrams", icon: "git-branch" },
      { path: "/spec-writer", labelKey: "aiflow.menu.specWriter", icon: "file-plus" },
      { path: "/media", labelKey: "aiflow.menu.mediaProcessing", icon: "headphones" },
      { path: "/cubix", labelKey: "aiflow.menu.cubixCourse", icon: "book" },
      { path: "/rpa", labelKey: "aiflow.menu.rpaBrowser", icon: "terminal" },
    ],
  },
];

/** SVG icon set — 24x24 viewBox, stroke-based (Untitled UI / Heroicons style) */
function MenuIcon({ name }: { name: string }) {
  const icons: Record<string, string> = {
    home: "M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z",
    "file-text": "M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z M14 2v6h6 M16 13H8 M16 17H8 M10 9H8",
    mail: "M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z M22 6l-10 7L2 6",
    "check-circle": "M22 11.08V12a10 10 0 11-5.93-9.14 M22 4L12 14.01l-3-3",
    "book-open": "M2 3h6a4 4 0 014 4v14a3 3 0 00-3-3H2z M22 3h-6a4 4 0 00-4 4v14a3 3 0 013-3h7z",
    "git-branch": "M6 3v12 M18 9a3 3 0 100-6 3 3 0 000 6z M6 21a3 3 0 100-6 3 3 0 000 6z M18 9a9 9 0 01-9 9",
    "file-plus": "M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z M14 2v6h6 M12 18v-6 M9 15h6",
    headphones: "M3 18v-6a9 9 0 0118 0v6 M21 19a2 2 0 01-2 2h-1a2 2 0 01-2-2v-3a2 2 0 012-2h3z M3 19a2 2 0 002 2h1a2 2 0 002-2v-3a2 2 0 00-2-2H3z",
    "play-circle": "M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z M10 8l6 4-6 4V8z",
    "trending-up": "M23 6l-9.5 9.5-5-5L1 18 M17 6h6v6",
    activity: "M22 12h-4l-3 9L9 3l-3 9H2",
    "bar-chart": "M12 20V10 M18 20V4 M6 20v-4",
    clock: "M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z M12 6v6l4 2",
    users: "M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2 M9 11a4 4 0 100-8 4 4 0 000 8z M23 21v-2a4 4 0 00-3-3.87 M16 3.13a4 4 0 010 7.75",
    layers: "M12 2L2 7l10 5 10-5-10-5z M2 17l10 5 10-5 M2 12l10 5 10-5",
    server: "M2 2h20v8H2z M2 14h20v8H2z M6 6h.01 M6 18h.01",
    terminal: "M4 17l6-6-6-6 M12 19h8",
    book: "M4 19.5A2.5 2.5 0 016.5 17H20 M4 19.5A2.5 2.5 0 014 17V5a2 2 0 012-2h14v14H6.5",
    chevronDown: "M6 9l6 6 6-6",
    chevronRight: "M9 18l6-6-6-6",
  };

  return (
    <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      {(icons[name] || icons["file-text"]).split(" M").map((segment, i) => (
        <path key={i} d={i === 0 ? segment : `M${segment}`} />
      ))}
    </svg>
  );
}

export function Sidebar() {
  const translate = useTranslate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>(() => {
    const saved = localStorage.getItem("aiflow_sidebar_groups");
    if (saved) {
      try { return JSON.parse(saved); } catch { /* use defaults */ }
    }
    return Object.fromEntries(MENU_GROUPS.map((g) => [g.labelKey, g.defaultOpen]));
  });

  useEffect(() => {
    localStorage.setItem("aiflow_sidebar_groups", JSON.stringify(openGroups));
  }, [openGroups]);

  // Auto-expand group containing active route (skip archive)
  useEffect(() => {
    for (const group of MENU_GROUPS) {
      if (group.archive) continue;
      if (group.items.some((item) => location.pathname.startsWith(item.path))) {
        setOpenGroups((prev) => ({ ...prev, [group.labelKey]: true }));
        break;
      }
    }
  }, [location.pathname]);

  // Responsive collapse at 768px
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 768px)");
    const handler = (e: MediaQueryListEvent | MediaQueryList) => setCollapsed(e.matches);
    handler(mq);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  const toggleGroup = (key: string) => {
    setOpenGroups((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const isGroupActive = (group: MenuGroup) =>
    !group.archive && group.items.some((item) => location.pathname.startsWith(item.path));

  const renderNavItem = (item: MenuItem, isArchive?: boolean) => {
    if (isArchive) {
      return (
        <NavLink
          key={item.path}
          to={item.path}
          title={collapsed ? translate(item.labelKey) : undefined}
          className={({ isActive }) =>
            `flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm transition-colors ${
              isActive
                ? "bg-brand-50 font-semibold text-brand-600 dark:bg-brand-900/30 dark:text-brand-400"
                : "text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:text-gray-500 dark:hover:bg-gray-800 dark:hover:text-gray-300"
            } ${collapsed ? "justify-center" : ""}`
          }
        >
          <MenuIcon name={item.icon} />
          {!collapsed && <span>{translate(item.labelKey)}</span>}
        </NavLink>
      );
    }
    return (
      <NavLink
        key={item.path}
        to={item.path}
        title={collapsed ? translate(item.labelKey) : undefined}
        className={({ isActive }) =>
          `flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm transition-colors ${
            isActive
              ? "bg-brand-50 font-semibold text-brand-600 dark:bg-brand-900/30 dark:text-brand-400"
              : "text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
          } ${collapsed ? "justify-center" : ""}`
        }
      >
        <MenuIcon name={item.icon} />
        {!collapsed && <span>{translate(item.labelKey)}</span>}
      </NavLink>
    );
  };

  return (
    <aside aria-label="Main navigation" className={`flex h-full flex-col border-r border-gray-200 bg-white transition-all dark:border-gray-700 dark:bg-gray-900 ${collapsed ? "w-14" : "w-[var(--sidebar-width)]"}`}>
      {/* Dashboard link */}
      <nav className="flex-1 overflow-y-auto px-2 py-2">
        <NavLink
          to="/"
          end
          title={collapsed ? "Dashboard" : undefined}
          className={({ isActive }) =>
            `flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              isActive
                ? "bg-brand-50 text-brand-600 dark:bg-brand-900/30 dark:text-brand-400"
                : "text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
            } ${collapsed ? "justify-center" : ""}`
          }
        >
          <MenuIcon name="home" />
          {!collapsed && <span>Dashboard</span>}
        </NavLink>

        {/* Menu groups */}
        {MENU_GROUPS.map((group) => (
          <div key={group.labelKey} className="mt-3">
            {/* Group header */}
            <button
              onClick={() => toggleGroup(group.labelKey)}
              title={collapsed ? translate(group.labelKey) : translate(group.labelKey)}
              className={`flex w-full min-w-0 items-center justify-between gap-1 px-3 py-1 text-xs font-semibold uppercase tracking-wider transition-colors ${
                group.archive
                  ? "text-gray-300 hover:text-gray-400 dark:text-gray-600 dark:hover:text-gray-500"
                  : isGroupActive(group)
                    ? "text-brand-500 dark:text-brand-400"
                    : "text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
              } ${collapsed ? "justify-center" : ""}`}
            >
              {!collapsed && <span className="truncate">{translate(group.labelKey)}</span>}
              {!collapsed && (
                <MenuIcon name={openGroups[group.labelKey] ? "chevronDown" : "chevronRight"} />
              )}
            </button>

            {/* Group items — archive items always rendered so they are discoverable */}
            {(openGroups[group.labelKey] || collapsed || group.archive) && (
              <div className="mt-1 space-y-0.5">
                {group.items.map((item) => renderNavItem(item, group.archive))}
              </div>
            )}
          </div>
        ))}
      </nav>
    </aside>
  );
}
