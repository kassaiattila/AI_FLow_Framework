// Lightweight i18n — no external dependencies
// Usage: const { t } = useTranslation();  t("sidebar.dashboard")

export type Locale = "hu" | "en";

const translations: Record<Locale, Record<string, string>> = {
  hu: {
    // Sidebar
    "sidebar.dashboard": "Dashboard",
    "sidebar.skills": "Skills",
    "sidebar.monitoring": "Monitoring",
    "sidebar.costs": "Koltsegek",
    "sidebar.runs": "Futasok",
    "sidebar.logout": "Kijelentkezes",
    "sidebar.light": "Vilagos",
    "sidebar.dark": "Sotet",

    // Skills
    "skill.invoice": "Szamlak",
    "skill.email": "Email Intent",
    "skill.rag": "RAG Chat",
    "skill.diagram": "Diagramok",
    "skill.cubix": "Cubix Kurzus",

    // Common
    "common.loading": "Betoltes...",
    "common.error": "Hiba",
    "common.retry": "Ujraprobalkozas",
    "common.save": "Mentes",
    "common.saving": "Mentes...",
    "common.saved": "Mentve!",
    "common.cancel": "Megse",
    "common.confirm": "Jovahagyas",
    "common.confirmAll": "Mind jovahagyva",
    "common.reset": "Visszaallitas",
    "common.export": "CSV Export",
    "common.print": "Nyomtatas",
    "common.send": "Kuldes",
    "common.generate": "Generalas",
    "common.noData": "Nincs adat",
    "common.readOnly": "Csak olvasas",

    // Pages
    "page.costs.title": "Koltseg Dashboard",
    "page.costs.subtitle": "LLM hasznalat es koltseg elemzes",
    "page.runs.title": "Workflow Futasok",
    "page.runs.subtitle": "Vegrehajtasi tortenelem es monitorozas",
    "page.login.title": "Bejelentkezes",
    "page.login.username": "Felhasznalonev",
    "page.login.password": "Jelszo",
    "page.login.submit": "Bejelentkezes",
    "page.login.failed": "Bejelentkezes sikertelen",

    // Invoice
    "invoice.title": "Invoice Processor",
    "invoice.upload": "Feltoltes",
    "invoice.process": "Feldolgozas",
    "invoice.verify": "Verifikalas",

    // Email
    "email.title": "Email Intent Processor",
    "email.processed": "Feldolgozott",
    "email.confidence": "Atl. confidence",
    "email.processing": "Atl. feldolgozas",

    // RAG
    "rag.title": "ASZF RAG Chat",
    "rag.placeholder": "Kerdes...",
    "rag.citations": "Hivatkozasok",
    "rag.search": "Kereses",
    "rag.pipeline": "Pipeline",

    // Process docs
    "processdoc.title": "Process Documentation",
    "processdoc.generate": "Diagram generalas",
    "processdoc.gallery": "Galeria",
    "processdoc.review": "Ertekeles",

    // Cubix
    "cubix.title": "Cubix Course Capture",
    "cubix.pipeline": "Pipeline",
    "cubix.structure": "Kurzus",
    "cubix.results": "Eredmenyek",

    // Audit
    "audit.title": "Audit naplo",
    "audit.edit": "Szerkesztes",
    "audit.confirm": "Jovahagyas",
    "audit.confirmAll": "Mind jovahagyva",
    "audit.reset": "Visszaallitas",
    "audit.noChanges": "Nincs valtozas",
  },
  en: {
    // Sidebar
    "sidebar.dashboard": "Dashboard",
    "sidebar.skills": "Skills",
    "sidebar.monitoring": "Monitoring",
    "sidebar.costs": "Costs",
    "sidebar.runs": "Runs",
    "sidebar.logout": "Logout",
    "sidebar.light": "Light",
    "sidebar.dark": "Dark",

    // Skills
    "skill.invoice": "Invoices",
    "skill.email": "Email Intent",
    "skill.rag": "RAG Chat",
    "skill.diagram": "Diagrams",
    "skill.cubix": "Cubix Course",

    // Common
    "common.loading": "Loading...",
    "common.error": "Error",
    "common.retry": "Retry",
    "common.save": "Save",
    "common.saving": "Saving...",
    "common.saved": "Saved!",
    "common.cancel": "Cancel",
    "common.confirm": "Confirm",
    "common.confirmAll": "Confirm all",
    "common.reset": "Reset",
    "common.export": "CSV Export",
    "common.print": "Print",
    "common.send": "Send",
    "common.generate": "Generate",
    "common.noData": "No data",
    "common.readOnly": "Read-only",

    // Pages
    "page.costs.title": "Cost Dashboard",
    "page.costs.subtitle": "LLM usage and cost analysis",
    "page.runs.title": "Workflow Runs",
    "page.runs.subtitle": "Execution history and monitoring",
    "page.login.title": "Sign In",
    "page.login.username": "Username",
    "page.login.password": "Password",
    "page.login.submit": "Sign In",
    "page.login.failed": "Login failed",

    // Invoice
    "invoice.title": "Invoice Processor",
    "invoice.upload": "Upload",
    "invoice.process": "Process",
    "invoice.verify": "Verify",

    // Email
    "email.title": "Email Intent Processor",
    "email.processed": "Processed",
    "email.confidence": "Avg confidence",
    "email.processing": "Avg processing",

    // RAG
    "rag.title": "ASZF RAG Chat",
    "rag.placeholder": "Question...",
    "rag.citations": "Citations",
    "rag.search": "Search",
    "rag.pipeline": "Pipeline",

    // Process docs
    "processdoc.title": "Process Documentation",
    "processdoc.generate": "Generate diagram",
    "processdoc.gallery": "Gallery",
    "processdoc.review": "Review",

    // Cubix
    "cubix.title": "Cubix Course Capture",
    "cubix.pipeline": "Pipeline",
    "cubix.structure": "Course",
    "cubix.results": "Results",

    // Audit
    "audit.title": "Audit log",
    "audit.edit": "Edit",
    "audit.confirm": "Confirm",
    "audit.confirmAll": "Confirm all",
    "audit.reset": "Reset",
    "audit.noChanges": "No changes",
  },
};

let currentLocale: Locale = "hu";

export function getLocale(): Locale {
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem("aiflow_locale");
    if (stored === "hu" || stored === "en") return stored;
  }
  return "hu";
}

export function setLocale(locale: Locale) {
  currentLocale = locale;
  if (typeof window !== "undefined") {
    localStorage.setItem("aiflow_locale", locale);
  }
}

export function t(key: string): string {
  const locale = typeof window !== "undefined" ? getLocale() : currentLocale;
  return translations[locale][key] || key;
}

export function tWithLocale(key: string, locale: Locale): string {
  return translations[locale][key] || key;
}
