/**
 * AIFlow AppShell — main layout with sidebar + topbar + content area.
 * Replaces React Admin's <Admin> layout.
 */

import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { ErrorBoundary } from "../components-new/ErrorBoundary";
import { Breadcrumb } from "../components-new/Breadcrumb";

export function AppShell() {
  return (
    <div className="flex h-screen flex-col bg-surface-light dark:bg-surface-dark">
      <TopBar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto p-6">
          <Breadcrumb />
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
    </div>
  );
}
