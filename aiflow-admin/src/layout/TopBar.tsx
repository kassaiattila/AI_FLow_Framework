/**
 * AIFlow TopBar — logo, backend status, locale toggle, theme toggle, user menu.
 */

import { useTranslate, useLocale, LOCALES } from "../lib/i18n";
import { useBackendStatus, useTheme } from "../lib/hooks";
import { getUser, logout } from "../lib/auth";
import { useNavigate } from "react-router-dom";
import { NotificationBell } from "./NotificationBell";

export function TopBar() {
  const translate = useTranslate();
  const { locale, setLocale } = useLocale();
  const backendStatus = useBackendStatus();
  const { theme, toggleTheme } = useTheme();
  const user = getUser();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <header className="flex h-12 items-center justify-between border-b border-gray-200 bg-white px-4 dark:border-gray-700 dark:bg-gray-900">
      {/* Left: Logo */}
      <div className="flex items-center gap-2">
        <span className="text-lg font-bold text-brand-500">AI</span>
        <span className="text-lg font-semibold text-gray-800 dark:text-gray-200">Flow</span>
      </div>

      {/* Right: Status + Locale + Theme + User */}
      <div className="flex items-center gap-3">
        {/* Backend status */}
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ${
            backendStatus === "connected"
              ? "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400"
              : backendStatus === "offline"
                ? "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                : "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400"
          }`}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              backendStatus === "connected"
                ? "bg-green-500"
                : backendStatus === "offline"
                  ? "bg-red-500"
                  : "bg-gray-400"
            }`}
          />
          {translate(`aiflow.dashboard.${backendStatus}`)}
        </span>

        {/* Locale toggle */}
        <div className="flex rounded-md border border-gray-300 dark:border-gray-600">
          {LOCALES.map((loc) => (
            <button
              key={loc.code}
              onClick={() => setLocale(loc.code)}
              className={`px-2 py-0.5 text-xs font-medium transition-colors ${
                locale === loc.code
                  ? "bg-brand-500 text-white"
                  : "text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
              } ${loc.code === "hu" ? "rounded-l-md" : "rounded-r-md"}`}
            >
              {loc.code.toUpperCase()}
            </button>
          ))}
        </div>

        {/* Notifications */}
        <NotificationBell />

        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          className="rounded-md p-1 text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
          title={theme === "dark" ? "Light mode" : "Dark mode"}
        >
          {theme === "dark" ? (
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          ) : (
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
            </svg>
          )}
        </button>

        {/* User menu */}
        {user && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-600 dark:text-gray-400">{user.email}</span>
            <button
              onClick={handleLogout}
              className="rounded-md px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
            >
              {translate("common.auth.logout")}
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
