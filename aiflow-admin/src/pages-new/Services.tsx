/**
 * Service Catalog — unified view of all AIFlow services with pipeline integration.
 * S4: v1.2.1 Production Ready Sprint
 */

import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { fetchApi } from "../lib/api-client";
import { useTranslate } from "../lib/i18n";
import { PageLayout } from "../layout/PageLayout";

interface ServiceItem {
  name: string;
  status: string;
  description: string;
  has_adapter: boolean;
}

interface ServicesResponse {
  services: ServiceItem[];
  source: string;
}

function formatName(name: string): string {
  return name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function Services() {
  const translate = useTranslate();
  const navigate = useNavigate();
  const [services, setServices] = useState<ServiceItem[]>([]);
  const [source, setSource] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filterAdapter, setFilterAdapter] = useState<"all" | "yes" | "no">("all");

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchApi<ServicesResponse>("GET", "/api/v1/services/manager");
      setServices(res.services);
      setSource(res.source);
    } catch {
      setServices([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const filtered = services.filter((s) => {
    if (search && !s.name.toLowerCase().includes(search.toLowerCase())) return false;
    if (filterAdapter === "yes" && !s.has_adapter) return false;
    if (filterAdapter === "no" && s.has_adapter) return false;
    return true;
  });

  if (loading) {
    return (
      <PageLayout titleKey="aiflow.services.catalogTitle" subtitleKey="aiflow.services.catalogSubtitle">
        <div className="flex h-64 items-center justify-center">
          <span className="h-8 w-8 animate-spin rounded-full border-4 border-gray-300 border-t-brand-500" />
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout titleKey="aiflow.services.catalogTitle" subtitleKey="aiflow.services.catalogSubtitle" source={source}>
      {/* Filters */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={translate("aiflow.services.search")}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-brand-500 focus:outline-none dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
        />
        <select
          value={filterAdapter}
          onChange={(e) => setFilterAdapter(e.target.value as "all" | "yes" | "no")}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
        >
          <option value="all">{translate("aiflow.services.allServices")}</option>
          <option value="yes">{translate("aiflow.services.withAdapter")}</option>
          <option value="no">{translate("aiflow.services.withoutAdapter")}</option>
        </select>
        <span className="text-sm text-gray-500 dark:text-gray-400">
          {filtered.length} / {services.length}
        </span>
      </div>

      {/* Service grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {filtered.map((svc) => (
          <div
            key={svc.name}
            className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
          >
            <div className="mb-2 flex items-start justify-between">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                {formatName(svc.name)}
              </h3>
              <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                svc.status === "available"
                  ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                  : "bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400"
              }`}>
                {svc.status}
              </span>
            </div>
            <p className="mb-3 text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
              {svc.description}
            </p>
            <div className="flex items-center justify-between">
              {svc.has_adapter && (
                <span className="rounded bg-brand-50 px-1.5 py-0.5 text-[10px] font-medium text-brand-600 dark:bg-brand-900/30 dark:text-brand-400">
                  {translate("aiflow.services.pipelineReady")}
                </span>
              )}
              {!svc.has_adapter && <span />}
              {svc.has_adapter && (
                <button
                  onClick={() => navigate("/pipelines")}
                  className="text-xs font-medium text-brand-500 hover:text-brand-600"
                >
                  {translate("aiflow.services.runPipeline")} →
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="mt-8 text-center text-sm text-gray-400">
          {translate("aiflow.services.noResults")}
        </div>
      )}
    </PageLayout>
  );
}
