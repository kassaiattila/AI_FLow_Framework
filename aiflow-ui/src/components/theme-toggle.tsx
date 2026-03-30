"use client";

import { useEffect, useState } from "react";

export function ThemeToggle() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("aiflow_theme");
    const prefersDark = stored === "dark" || (!stored && window.matchMedia("(prefers-color-scheme: dark)").matches);
    setDark(prefersDark);
    document.documentElement.classList.toggle("dark", prefersDark);
  }, []);

  const toggle = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("aiflow_theme", next ? "dark" : "light");
  };

  return (
    <button
      onClick={toggle}
      className="flex items-center gap-1 px-2 py-1.5 rounded-md hover:bg-muted text-xs"
      title={dark ? "Vilagos mod" : "Sotet mod"}
    >
      {dark ? "\u2600\uFE0F Vilagos" : "\uD83C\uDF19 Sotet"}
    </button>
  );
}
