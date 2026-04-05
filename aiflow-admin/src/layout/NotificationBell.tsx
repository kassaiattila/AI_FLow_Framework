/**
 * NotificationBell — bell icon with unread badge and dropdown panel.
 * Fetches in-app notifications from /api/v1/notifications/in-app.
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { fetchApi } from "../lib/api-client";
import { getUser } from "../lib/auth";
import { useTranslate } from "../lib/i18n";

interface InAppNotification {
  id: string;
  user_id: string;
  title: string;
  body: string | null;
  link: string | null;
  read: boolean;
  created_at: string | null;
}

interface InAppListResponse {
  notifications: InAppNotification[];
  total: number;
  source: string;
}

interface UnreadCountResponse {
  count: number;
  source: string;
}

function timeAgo(dateStr: string | null, translate: (k: string) => string): string {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return translate("aiflow.notifications.justNow");
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  return `${days}d`;
}

export function NotificationBell() {
  const translate = useTranslate();
  const user = getUser();
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const [notifications, setNotifications] = useState<InAppNotification[]>([]);
  const [loading, setLoading] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  const userParam = user?.id ? `?user_id=${user.id}` : "";

  // Fetch unread count (poll every 30s)
  const fetchUnread = useCallback(async () => {
    try {
      const res = await fetchApi<UnreadCountResponse>(
        "GET",
        `/api/v1/notifications/in-app/unread-count${userParam}`,
      );
      setUnread(res.count);
    } catch {
      // silent — bell still shows, just no count
    }
  }, [userParam]);

  useEffect(() => {
    fetchUnread();
    const interval = setInterval(fetchUnread, 30000);
    return () => clearInterval(interval);
  }, [fetchUnread]);

  // Fetch notification list when panel opens
  const fetchList = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchApi<InAppListResponse>(
        "GET",
        `/api/v1/notifications/in-app${userParam}&limit=10`,
      );
      setNotifications(res.notifications);
    } catch {
      setNotifications([]);
    } finally {
      setLoading(false);
    }
  }, [userParam]);

  const handleToggle = () => {
    const next = !open;
    setOpen(next);
    if (next) fetchList();
  };

  // Mark single as read
  const handleMarkRead = async (id: string) => {
    await fetchApi("POST", `/api/v1/notifications/in-app/${id}/read`);
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n)),
    );
    setUnread((prev) => Math.max(0, prev - 1));
  };

  // Mark all as read
  const handleMarkAllRead = async () => {
    await fetchApi("POST", `/api/v1/notifications/in-app/read-all${userParam}`);
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    setUnread(0);
  };

  // Close on click outside
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  return (
    <div ref={panelRef} className="relative">
      {/* Bell button */}
      <button
        onClick={handleToggle}
        className="relative rounded-md p-1 text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
        aria-label={translate("aiflow.notifications.title")}
      >
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
        </svg>
        {unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </button>

      {/* Dropdown panel */}
      {open && (
        <div className="absolute right-0 top-full z-50 mt-2 w-80 rounded-lg border border-gray-200 bg-white shadow-lg dark:border-gray-700 dark:bg-gray-900">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-gray-200 px-4 py-2.5 dark:border-gray-700">
            <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              {translate("aiflow.notifications.title")}
            </span>
            {unread > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="text-xs font-medium text-brand-500 hover:text-brand-600"
              >
                {translate("aiflow.notifications.markAllRead")}
              </button>
            )}
          </div>

          {/* Notification list */}
          <div className="max-h-80 overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center py-6">
                <span className="h-5 w-5 animate-spin rounded-full border-2 border-gray-300 border-t-brand-500" />
              </div>
            ) : notifications.length === 0 ? (
              <div className="py-6 text-center text-sm text-gray-400 dark:text-gray-500">
                {translate("aiflow.notifications.empty")}
              </div>
            ) : (
              notifications.map((n) => (
                <button
                  key={n.id}
                  onClick={() => {
                    if (!n.read) handleMarkRead(n.id);
                    if (n.link) {
                      window.location.hash = n.link;
                      setOpen(false);
                    }
                  }}
                  className={`flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/50 ${
                    !n.read ? "bg-brand-50/50 dark:bg-brand-900/10" : ""
                  }`}
                >
                  {/* Unread dot */}
                  <div className="mt-1.5 shrink-0">
                    {!n.read ? (
                      <span className="block h-2 w-2 rounded-full bg-brand-500" />
                    ) : (
                      <span className="block h-2 w-2" />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className={`text-sm ${!n.read ? "font-medium text-gray-900 dark:text-gray-100" : "text-gray-600 dark:text-gray-400"}`}>
                      {n.title}
                    </p>
                    {n.body && (
                      <p className="mt-0.5 truncate text-xs text-gray-500 dark:text-gray-500">
                        {n.body}
                      </p>
                    )}
                    <p className="mt-1 text-xs text-gray-400">
                      {timeAgo(n.created_at, translate)}
                    </p>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
