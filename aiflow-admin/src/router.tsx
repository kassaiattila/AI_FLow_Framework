/**
 * AIFlow Router — React Router v7 configuration with auth guard.
 * During F6.0, old MUI pages are wrapped and served through the new shell.
 * They will be replaced one by one in F6.1-F6.5.
 */

import { createHashRouter, Navigate } from "react-router-dom";
import { AppShell } from "./layout/AppShell";
import { Login } from "./pages-new/Login";
import { isAuthenticated } from "./lib/auth";
import type { ReactNode } from "react";

// --- NEW Tailwind pages (F6.1+) ---
import { DashboardNew } from "./pages-new/Dashboard";
import { Documents as DocumentsNew } from "./pages-new/Documents";
import { Emails as EmailsNew } from "./pages-new/Emails";
import { Rag as RagNew } from "./pages-new/Rag";
import { ProcessDocs as ProcessDocsNew } from "./pages-new/ProcessDocs";
import { Media as MediaNew } from "./pages-new/Media";
import { Rpa as RpaNew } from "./pages-new/Rpa";
import { Reviews as ReviewsNew } from "./pages-new/Reviews";

// --- Old MUI pages (temporary, will be replaced in F6.2-F6.5) ---
import { ProcessDocViewer } from "./pages/ProcessDocViewer";
import { RagChat } from "./pages/RagChat";
import { CubixViewer } from "./pages/CubixViewer";
import { DocumentUpload } from "./pages/DocumentUpload";
import { EmailUpload } from "./pages/EmailUpload";
import { EmailConnectors } from "./pages/EmailConnectors";
import { CostsPage } from "./pages/CostsPage";
import { CollectionManager } from "./pages/CollectionManager";
import { CollectionDetail } from "./pages/CollectionDetail";
import { MediaViewer } from "./pages/MediaViewer";
import { RpaViewer } from "./pages/RpaViewer";
import { ReviewQueue } from "./pages/ReviewQueue";
import { MonitoringDashboard } from "./pages/MonitoringDashboard";
import { AuditLog } from "./pages/AuditLog";
import { AdminPage } from "./pages/AdminPage";
import { VerificationPanel } from "./verification/VerificationPanel";
import { RunList } from "./resources/RunList";
import { RunShow } from "./resources/RunShow";
import { DocumentList } from "./resources/DocumentList";
import { DocumentShow } from "./resources/DocumentShow";
import { EmailList } from "./resources/EmailList";
import { EmailShow } from "./resources/EmailShow";

/** Auth guard — redirects to /login if not authenticated */
function RequireAuth({ children }: { children: ReactNode }) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

/**
 * Wrapper for old MUI pages in the new Tailwind shell.
 * Provides a neutral container that doesn't conflict with MUI styles.
 */
function LegacyPage({ children }: { children: ReactNode }) {
  return <div className="legacy-mui-wrapper">{children}</div>;
}

export const router = createHashRouter([
  {
    path: "/login",
    element: <Login />,
  },
  {
    path: "/",
    element: (
      <RequireAuth>
        <AppShell />
      </RequireAuth>
    ),
    children: [
      // Dashboard (NEW Tailwind — F6.1)
      { index: true, element: <DashboardNew /> },

      // Runs (old MUI, replaced in F6.5)
      { path: "runs", element: <LegacyPage><RunList /></LegacyPage> },
      { path: "runs/:id", element: <LegacyPage><RunShow /></LegacyPage> },

      // Documents (NEW Tailwind — F6.2)
      { path: "documents", element: <DocumentsNew /> },
      { path: "documents/:id/verify", element: <LegacyPage><VerificationPanel /></LegacyPage> },
      { path: "document-upload", element: <Navigate to="/documents" replace /> },

      // Emails (NEW Tailwind — F6.3)
      { path: "emails", element: <EmailsNew /> },
      { path: "email-upload", element: <Navigate to="/emails" replace /> },
      { path: "email-connectors", element: <Navigate to="/emails" replace /> },

      // Costs (old MUI, replaced in F6.5)
      { path: "costs", element: <LegacyPage><CostsPage /></LegacyPage> },

      // RAG (NEW Tailwind — F6.4)
      { path: "rag", element: <RagNew /> },
      { path: "rag/collections", element: <Navigate to="/rag" replace /> },
      { path: "rag/collections/:id", element: <RagNew /> },
      { path: "rag/:id", element: <RagNew /> },
      { path: "rag-chat", element: <Navigate to="/rag" replace /> },

      // AI Services (NEW Tailwind — F6.4)
      { path: "process-docs", element: <ProcessDocsNew /> },
      { path: "media", element: <MediaNew /> },
      { path: "rpa", element: <RpaNew /> },
      { path: "reviews", element: <ReviewsNew /> },
      { path: "cubix", element: <LegacyPage><CubixViewer /></LegacyPage> },

      // Operations (old MUI, replaced in F6.5)
      { path: "monitoring", element: <LegacyPage><MonitoringDashboard /></LegacyPage> },
      { path: "audit", element: <LegacyPage><AuditLog /></LegacyPage> },
      { path: "admin", element: <LegacyPage><AdminPage /></LegacyPage> },
      { path: "admin/users", element: <Navigate to="/admin" replace /> },
    ],
  },
]);
