/**
 * AIFlow i18n — replaces React Admin's ra-i18n-polyglot.
 * Simple useTranslate() hook with HU/EN JSON file support.
 */

import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import hu from "../locales/hu.json";
import en from "../locales/en.json";

export type Locale = "hu" | "en";

interface I18nContextType {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  translate: (key: string, params?: Record<string, string | number>) => string;
}

const translations: Record<Locale, Record<string, unknown>> = { hu, en };

/** Resolve a dot-separated key like "aiflow.dashboard.title" from a nested object */
function resolveKey(
  obj: Record<string, unknown>,
  key: string,
): string | undefined {
  const parts = key.split(".");
  let current: unknown = obj;
  for (const part of parts) {
    if (current == null || typeof current !== "object") return undefined;
    current = (current as Record<string, unknown>)[part];
  }
  return typeof current === "string" ? current : undefined;
}

/** Replace %{param} placeholders */
function interpolate(
  text: string,
  params?: Record<string, string | number>,
): string {
  if (!params) return text;
  return text.replace(/%\{(\w+)\}/g, (_, key) =>
    String(params[key] ?? `%{${key}}`),
  );
}

const LOCALE_KEY = "aiflow_locale";

function getInitialLocale(): Locale {
  const stored = localStorage.getItem(LOCALE_KEY);
  if (stored === "hu" || stored === "en") return stored;
  return "hu";
}

const I18nContext = createContext<I18nContextType | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(getInitialLocale);

  const setLocale = useCallback((newLocale: Locale) => {
    setLocaleState(newLocale);
    localStorage.setItem(LOCALE_KEY, newLocale);
  }, []);

  const translate = useCallback(
    (key: string, params?: Record<string, string | number>): string => {
      const text = resolveKey(
        translations[locale] as Record<string, unknown>,
        key,
      );
      if (text) return interpolate(text, params);
      // Fallback: try other locale
      const fallback = resolveKey(
        translations[locale === "hu" ? "en" : "hu"] as Record<string, unknown>,
        key,
      );
      if (fallback) return interpolate(fallback, params);
      // Last resort: return key itself
      return key;
    },
    [locale],
  );

  return (
    <I18nContext.Provider value={{ locale, setLocale, translate }}>
      {children}
    </I18nContext.Provider>
  );
}

/** Hook to access translate function and locale */
export function useTranslate() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useTranslate must be used within I18nProvider");
  return ctx.translate;
}

/** Hook to access locale and setLocale */
export function useLocale() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useLocale must be used within I18nProvider");
  return { locale: ctx.locale, setLocale: ctx.setLocale };
}

export const LOCALES = [
  { code: "hu" as const, name: "Magyar" },
  { code: "en" as const, name: "English" },
];
