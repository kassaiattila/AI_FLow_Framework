/**
 * AIFlow Sidebar — 4 collapsible groups, 11 items, active state.
 * Replaces React Admin's Menu component.
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
}

const MENU_GROUPS: MenuGroup[] = [
  {
    labelKey: "aiflow.menu.operations",
    defaultOpen: true,
    items: [
      { path: "/runs", labelKey: "aiflow.resources.runs", icon: "play" },
      { path: "/costs", labelKey: "aiflow.costs.title", icon: "dollar" },
      { path: "/monitoring", labelKey: "aiflow.monitoring.title", icon: "heart" },
    ],
  },
  {
    labelKey: "aiflow.menu.data",
    defaultOpen: true,
    items: [
      { path: "/documents", labelKey: "aiflow.resources.documents", icon: "file" },
      { path: "/emails", labelKey: "aiflow.resources.emails", icon: "mail" },
    ],
  },
  {
    labelKey: "aiflow.menu.aiServices",
    defaultOpen: true,
    items: [
      { path: "/rag", labelKey: "aiflow.rag.title", icon: "book" },
      { path: "/process-docs", labelKey: "aiflow.skills.process_documentation", icon: "diagram" },
      { path: "/media", labelKey: "aiflow.media.title", icon: "audio" },
      { path: "/rpa", labelKey: "aiflow.rpa.menuLabel", icon: "bot" },
    ],
  },
  {
    labelKey: "aiflow.menu.admin",
    defaultOpen: false,
    items: [
      { path: "/admin", labelKey: "aiflow.admin.menuLabel", icon: "users" },
      { path: "/audit", labelKey: "aiflow.audit.title", icon: "history" },
      { path: "/reviews", labelKey: "aiflow.reviews.menuLabel", icon: "check" },
    ],
  },
];

/** Simple SVG icon set — will be replaced by @untitledui/icons */
function MenuIcon({ name }: { name: string }) {
  const icons: Record<string, string> = {
    play: "M5 3l14 9-14 9V3z",
    dollar: "M12 1v22M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6",
    heart: "M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z",
    file: "M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z M14 2v6h6",
    mail: "M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z M22 6l-10 7L2 6",
    book: "M4 19.5A2.5 2.5 0 016.5 17H20 M4 19.5A2.5 2.5 0 014 17V5a2 2 0 012-2h14v14H6.5",
    diagram: "M22 12h-4l-3 9L9 3l-3 9H2",
    audio: "M9 18V5l12-2v13 M9 18a3 3 0 11-6 0 3 3 0 016 0z",
    bot: "M12 8V4l8 4-8 4V8zM4 12h8m-8 4h16",
    users: "M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2 M9 11a4 4 0 100-8 4 4 0 000 8z M23 21v-2a4 4 0 00-3-3.87 M16 3.13a4 4 0 010 7.75",
    history: "M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z",
    check: "M9 11l3 3L22 4 M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11",
    home: "M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z",
    chevronDown: "M6 9l6 6 6-6",
    chevronRight: "M9 18l6-6-6-6",
  };

  return (
    <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d={icons[name] || icons.file} />
    </svg>
  );
}

export function Sidebar() {
  const translate = useTranslate();
  const location = useLocation();
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>(() => {
    const saved = localStorage.getItem("aiflow_sidebar_groups");
    if (saved) return JSON.parse(saved);
    return Object.fromEntries(MENU_GROUPS.map((g) => [g.labelKey, g.defaultOpen]));
  });

  useEffect(() => {
    localStorage.setItem("aiflow_sidebar_groups", JSON.stringify(openGroups));
  }, [openGroups]);

  // Auto-expand group containing active route
  useEffect(() => {
    for (const group of MENU_GROUPS) {
      if (group.items.some((item) => location.pathname.startsWith(item.path))) {
        setOpenGroups((prev) => ({ ...prev, [group.labelKey]: true }));
        break;
      }
    }
  }, [location.pathname]);

  const toggleGroup = (key: string) => {
    setOpenGroups((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <aside className="flex h-full w-[var(--sidebar-width)] flex-col border-r border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900">
      {/* Dashboard link */}
      <nav className="flex-1 overflow-y-auto px-2 py-2">
        <NavLink
          to="/"
          end
          className={({ isActive }) =>
            `flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              isActive
                ? "bg-brand-50 text-brand-600 dark:bg-brand-900/30 dark:text-brand-400"
                : "text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
            }`
          }
        >
          <MenuIcon name="home" />
          <span>Dashboard</span>
        </NavLink>

        {/* Menu groups */}
        {MENU_GROUPS.map((group) => (
          <div key={group.labelKey} className="mt-3">
            {/* Group header */}
            <button
              onClick={() => toggleGroup(group.labelKey)}
              className="flex w-full items-center justify-between px-3 py-1 text-xs font-semibold uppercase tracking-wider text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
            >
              <span>{translate(group.labelKey)}</span>
              <MenuIcon name={openGroups[group.labelKey] ? "chevronDown" : "chevronRight"} />
            </button>

            {/* Group items */}
            {openGroups[group.labelKey] && (
              <div className="mt-1 space-y-0.5">
                {group.items.map((item) => (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={({ isActive }) =>
                      `flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm transition-colors ${
                        isActive
                          ? "bg-brand-50 font-semibold text-brand-600 dark:bg-brand-900/30 dark:text-brand-400"
                          : "text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
                      }`
                    }
                  >
                    <MenuIcon name={item.icon} />
                    <span>{translate(item.labelKey)}</span>
                  </NavLink>
                ))}
              </div>
            )}
          </div>
        ))}
      </nav>
    </aside>
  );
}
