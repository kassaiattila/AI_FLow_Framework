"use client";

import { useState, useEffect, useCallback } from "react";
import { getLocale, setLocale, tWithLocale, type Locale } from "@/lib/i18n";

// Custom event to sync locale across all useI18n instances
const LOCALE_CHANGE_EVENT = "aiflow-locale-change";

export function useI18n() {
  const [locale, setLocaleState] = useState<Locale>("hu");

  useEffect(() => {
    // Read persisted locale on mount
    setLocaleState(getLocale());

    // Listen for locale changes from other components
    const handler = () => setLocaleState(getLocale());
    window.addEventListener(LOCALE_CHANGE_EVENT, handler);
    return () => window.removeEventListener(LOCALE_CHANGE_EVENT, handler);
  }, []);

  const switchLocale = useCallback((newLocale: Locale) => {
    setLocale(newLocale);
    setLocaleState(newLocale);
    // Notify all other useI18n instances
    window.dispatchEvent(new Event(LOCALE_CHANGE_EVENT));
  }, []);

  const t = useCallback((key: string) => tWithLocale(key, locale), [locale]);

  return { locale, switchLocale, t };
}
