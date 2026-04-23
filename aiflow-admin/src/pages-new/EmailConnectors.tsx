/**
 * AIFlow EmailConnectors — S108b standalone page.
 * Wraps the ConnectorsTab exported from Emails.tsx so the large connector
 * CRUD + fetch flow gets its own route without duplicating the logic.
 */

import { useNavigate } from "react-router-dom";
import { useTranslate } from "../lib/i18n";
import { PageLayout } from "../layout/PageLayout";
import { ConnectorsTab } from "./Emails";

export function EmailConnectors() {
  const navigate = useNavigate();
  const translate = useTranslate();

  return (
    <PageLayout titleKey="aiflow.connectors.menuLabel" subtitleKey="aiflow.emails.connectorsSubtitle">
      <div className="mb-4 flex items-center gap-3">
        <button
          onClick={() => navigate("/emails")}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400"
        >
          ← {translate("common.action.back")}
        </button>
      </div>
      <ConnectorsTab />
    </PageLayout>
  );
}
