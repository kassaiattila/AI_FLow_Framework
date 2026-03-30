"use client";

import { useState, useEffect, useCallback } from "react";
import { getLocale, setLocale, tWithLocale, type Locale } from "@/lib/i18n";

export function useI18n() {
  // Always start with "hu" to match server render — prevents hydration mismatch
  const [locale, setLocaleState] = useState<Locale>("hu");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setLocaleState(getLocale());
    setMounted(true);
  }, []);

  const switchLocale = useCallback((newLocale: Locale) => {
    setLocale(newLocale);
    setLocaleState(newLocale);
  }, []);

  // Use React state locale (not localStorage) to avoid mismatch
  const t = useCallback((key: string) => tWithLocale(key, locale), [locale]);

  return { locale, switchLocale, t, mounted };
}
