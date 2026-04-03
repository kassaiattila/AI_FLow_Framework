/**
 * AIFlow Router — React Router v7 configuration with auth guard.
 * F6.6: All pages migrated to Tailwind. Only Cubix remains as legacy.
 */

import { createHashRouter, Navigate } from "react-router-dom";
import { AppShell } from "./layout/AppShell";
import { Login } from "./pages-new/Login";
import { isAuthenticated } from "./lib/auth";
import type { ReactNode } from "react";

// --- Tailwind pages ---
import { DashboardNew } from "./pages-new/Dashboard";
import { Documents as DocumentsNew } from "./pages-new/Documents";
import { Emails as EmailsNew } from "./pages-new/Emails";
import { Rag as RagNew } from "./pages-new/Rag";
import { RagDetail } from "./pages-new/RagDetail";
import { ProcessDocs as ProcessDocsNew } from "./pages-new/ProcessDocs";
import { Media as MediaNew } from "./pages-new/Media";
import { Rpa as RpaNew } from "./pages-new/Rpa";
import { Reviews as ReviewsNew } from "./pages-new/Reviews";
import { Runs as RunsNew } from "./pages-new/Runs";
import { Costs as CostsNew } from "./pages-new/Costs";
import { Monitoring as MonitoringNew } from "./pages-new/Monitoring";
import { Audit as AuditNew } from "./pages-new/Audit";
import { Admin as AdminNew } from "./pages-new/Admin";
import { Verification } from "./pages-new/Verification";
import { DocumentDetail } from "./pages-new/DocumentDetail";

// --- Legacy MUI (to be migrated in future) ---
import { CubixViewer } from "./pages/CubixViewer";

/** Auth guard */
function RequireAuth({ children }: { children: ReactNode }) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

/** Legacy wrapper for remaining MUI pages */
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
      // Dashboard
      { index: true, element: <DashboardNew /> },

      // Operations
      { path: "runs", element: <RunsNew /> },
      { path: "costs", element: <CostsNew /> },
      { path: "monitoring", element: <MonitoringNew /> },

      // Data
      { path: "documents", element: <DocumentsNew /> },
      { path: "documents/:id/show", element: <DocumentDetail /> },
      { path: "documents/:id/verify", element: <Verification /> },
      { path: "document-upload", element: <Navigate to="/documents" replace /> },
      { path: "emails", element: <EmailsNew /> },
      { path: "email-upload", element: <Navigate to="/emails" replace /> },
      { path: "email-connectors", element: <Navigate to="/emails" replace /> },

      // AI Services
      { path: "rag", element: <RagNew /> },
      { path: "rag/collections", element: <Navigate to="/rag" replace /> },
      { path: "rag/collections/:id", element: <RagDetail /> },
      { path: "rag/:id", element: <RagDetail /> },
      { path: "rag-chat", element: <Navigate to="/rag" replace /> },
      { path: "process-docs", element: <ProcessDocsNew /> },
      { path: "media", element: <MediaNew /> },
      { path: "rpa", element: <RpaNew /> },
      { path: "reviews", element: <ReviewsNew /> },
      { path: "cubix", element: <LegacyPage><CubixViewer /></LegacyPage> },

      // Admin
      { path: "audit", element: <AuditNew /> },
      { path: "admin", element: <AdminNew /> },
      { path: "admin/users", element: <Navigate to="/admin" replace /> },
    ],
  },
]);
