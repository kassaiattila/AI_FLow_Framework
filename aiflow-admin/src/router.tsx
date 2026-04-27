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
import { EmailDetail } from "./pages-new/EmailDetail";
import { EmailConnectors } from "./pages-new/EmailConnectors";
import { IntentRules } from "./pages-new/IntentRules";
import { Rag as RagNew } from "./pages-new/Rag";
import { RagCollections } from "./pages-new/RagCollections";
import { DocumentRecognizer } from "./pages-new/DocumentRecognizer";
import { RagDetail } from "./pages-new/RagDetail";
// J4 archived pages — redirected to dashboard (Sprint C)
import { Reviews as ReviewsNew } from "./pages-new/Reviews";
import { Runs as RunsNew } from "./pages-new/Runs";
import { RunDetail } from "./pages-new/RunDetail";
import { Costs as CostsNew } from "./pages-new/Costs";
import { BudgetManagement } from "./pages-new/BudgetManagement";
import { Monitoring as MonitoringNew } from "./pages-new/Monitoring";
import { Audit as AuditNew } from "./pages-new/Audit";
import { Admin as AdminNew } from "./pages-new/Admin";
import { Verification } from "./pages-new/Verification";
import { DocumentDetail } from "./pages-new/DocumentDetail";
import { PackageDetail } from "./pages-new/PackageDetail";
import { Pipelines } from "./pages-new/Pipelines";
import { PipelineDetail } from "./pages-new/PipelineDetail";
import { Prompts } from "./pages-new/Prompts";
import { PromptDetail } from "./pages-new/PromptDetail";
import { PromptWorkflows } from "./pages-new/PromptWorkflows";
import { Quality } from "./pages-new/Quality";
import { RoutingRuns } from "./pages-new/RoutingRuns";
import { Services } from "./pages-new/Services";
// Cubix archived (Sprint C)

/** Auth guard */
function RequireAuth({ children }: { children: ReactNode }) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
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
      { path: "runs/:id", element: <RunDetail /> },
      { path: "costs", element: <CostsNew /> },
      { path: "budget-management", element: <BudgetManagement /> },
      { path: "monitoring", element: <MonitoringNew /> },
      { path: "quality", element: <Quality /> },

      // Data
      { path: "documents", element: <DocumentsNew /> },
      { path: "documents/:id/show", element: <DocumentDetail /> },
      { path: "documents/:id/verify", element: <Verification /> },
      { path: "packages/:id", element: <PackageDetail /> },
      { path: "prompts", element: <Prompts /> },
      // Workflows route MUST come before the prompts/* catch-all.
      { path: "prompts/workflows", element: <PromptWorkflows /> },
      { path: "prompts/*", element: <PromptDetail /> },
      {
        path: "document-upload",
        element: <Navigate to="/documents" replace />,
      },
      { path: "emails", element: <EmailsNew /> },
      { path: "emails/connectors", element: <EmailConnectors /> },
      { path: "emails/intent-rules", element: <IntentRules /> },
      { path: "emails/intent-rules/:tenantId", element: <IntentRules /> },
      { path: "routing-runs", element: <RoutingRuns /> },
      { path: "emails/:id", element: <EmailDetail /> },
      { path: "email-upload", element: <Navigate to="/emails" replace /> },
      { path: "email-connectors", element: <Navigate to="/emails" replace /> },

      // AI Services
      { path: "rag", element: <RagNew /> },
      { path: "rag/collections", element: <RagCollections /> },
      // Sprint V SV-4 — generic document recognizer admin page
      { path: "document-recognizer", element: <DocumentRecognizer /> },
      { path: "rag/collections/:id", element: <RagDetail /> },
      { path: "rag/:id", element: <RagDetail /> },
      { path: "rag-chat", element: <Navigate to="/rag" replace /> },
      { path: "process-docs", element: <Navigate to="/" replace /> },
      { path: "spec-writer", element: <Navigate to="/" replace /> },
      { path: "media", element: <Navigate to="/" replace /> },
      { path: "rpa", element: <Navigate to="/" replace /> },
      { path: "reviews", element: <ReviewsNew /> },
      { path: "cubix", element: <Navigate to="/" replace /> },

      // Orchestration (v1.2.0)
      { path: "services", element: <Services /> },
      { path: "pipelines", element: <Pipelines /> },
      { path: "pipelines/:id", element: <PipelineDetail /> },

      // Admin
      { path: "audit", element: <AuditNew /> },
      { path: "admin", element: <AdminNew /> },
      { path: "admin/users", element: <Navigate to="/admin" replace /> },
    ],
  },
]);
