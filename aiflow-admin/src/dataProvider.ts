import { DataProvider } from "react-admin";

// Source tracking — stores the last known data source per resource
const sourceCache = new Map<string, string>();
export function getResourceSource(resource: string): string | null {
  return sourceCache.get(resource) || null;
}

// Maps react-admin resource names to API endpoints and response shapes
const RESOURCE_MAP: Record<string, { endpoint: string; listKey: string; idField: string }> = {
  runs: { endpoint: "/api/runs", listKey: "runs", idField: "run_id" },
  invoices: { endpoint: "/api/documents", listKey: "documents", idField: "source_file" },
  emails: { endpoint: "/api/emails", listKey: "emails", idField: "email_id" },
  "process-docs": { endpoint: "/api/process-docs", listKey: "documents", idField: "doc_id" },
  cubix: { endpoint: "/api/cubix", listKey: "courses", idField: "course_id" },
};

async function fetchJson(url: string, options?: RequestInit) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// Deep get nested value by dot-path (e.g., "vendor.name")
function getNestedValue(obj: Record<string, unknown>, path: string): unknown {
  return path.split(".").reduce((acc: unknown, key) => {
    if (acc && typeof acc === "object") return (acc as Record<string, unknown>)[key];
    return undefined;
  }, obj);
}

export const dataProvider: DataProvider = {
  async getList(resource, params) {
    const config = RESOURCE_MAP[resource];
    if (!config) throw new Error(`Unknown resource: ${resource}`);

    const { page = 1, perPage = 25 } = params.pagination || {};
    const url = new URL(config.endpoint, window.location.origin);

    // Pass skill filter for runs
    if (resource === "runs" && params.filter?.skill) {
      url.searchParams.set("skill", params.filter.skill);
    }

    const json = await fetchJson(url.toString());
    if (json.source) sourceCache.set(resource, json.source);
    let allData = (json[config.listKey] || []).map((item: Record<string, unknown>) => ({
      ...item,
      id: item[config.idField] || item.id,
    }));

    // Client-side filtering
    const filter = params.filter || {};
    for (const [key, value] of Object.entries(filter)) {
      if (!value || (typeof value === "string" && !value.trim())) continue;
      // Special filter: only processed invoices (has real vendor name and non-zero total)
      if (key === "_processed" && value === true && resource === "invoices") {
        allData = allData.filter((item: Record<string, unknown>) => {
          const vendor = item.vendor as Record<string, unknown> | undefined;
          const totals = item.totals as Record<string, unknown> | undefined;
          const grossTotal = (totals?.gross_total as number) || 0;
          const vendorName = (vendor?.name as string) || "";
          return grossTotal > 0 || (vendorName && vendorName.length > 3);
        });
        continue;
      }
      if (key === "q" && typeof value === "string") {
        // Global search on key fields (not JSON.stringify — too slow/broad)
        const q = value.toLowerCase();
        const searchFields = ["skill_name", "status", "run_id", "source_file", "vendor.name",
          "header.invoice_number", "sender", "subject", "email_id"];
        allData = allData.filter((item: Record<string, unknown>) =>
          searchFields.some((f) => {
            const v = getNestedValue(item, f);
            return v != null && String(v).toLowerCase().includes(q);
          })
        );
      } else if (typeof value === "string") {
        allData = allData.filter((item: Record<string, unknown>) => {
          const fieldVal = getNestedValue(item, key);
          if (fieldVal == null) return false;
          return String(fieldVal).toLowerCase().includes(value.toLowerCase());
        });
      }
    }

    // Client-side sorting
    const { field, order } = params.sort || { field: "id", order: "ASC" };
    allData.sort((a: Record<string, unknown>, b: Record<string, unknown>) => {
      const aVal = getNestedValue(a, field);
      const bVal = getNestedValue(b, field);
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      const cmp = typeof aVal === "number" && typeof bVal === "number"
        ? aVal - bVal
        : String(aVal).localeCompare(String(bVal));
      return order === "DESC" ? -cmp : cmp;
    });

    // Client-side pagination
    const start = (page - 1) * perPage;
    const data = allData.slice(start, start + perPage);

    return { data, total: allData.length };
  },

  async getOne(resource, params) {
    const config = RESOURCE_MAP[resource];
    if (!config) throw new Error(`Unknown resource: ${resource}`);

    // For resources with dedicated endpoints
    if (resource === "emails") {
      const json = await fetchJson(`/api/emails/${params.id}`);
      if (json.source) sourceCache.set(resource, json.source);
      return { data: { ...json, id: json[config.idField] || json.id } };
    }

    // Fallback: load full list and find by ID
    const json = await fetchJson(config.endpoint);
    const list = json[config.listKey] || [];
    const item = list.find((i: Record<string, unknown>) => i[config.idField] === params.id || i.id === params.id);
    if (!item) throw new Error("Not found");
    return { data: { ...item, id: item[config.idField] || item.id } };
  },

  async create(resource, params) {
    if (resource === "process-docs") {
      const json = await fetchJson("/api/process-docs/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_input: params.data.user_input }),
      });
      return { data: { ...json, id: json.doc_id } };
    }
    throw new Error(`Create not supported for: ${resource}`);
  },

  // Stubs for required DataProvider methods
  async update() { throw new Error("Not implemented"); },
  async updateMany() { throw new Error("Not implemented"); },
  async delete() { throw new Error("Not implemented"); },
  async deleteMany() { throw new Error("Not implemented"); },
  async getMany(resource, params) {
    const results = await Promise.all(
      params.ids.map((id) => dataProvider.getOne(resource, { id }))
    );
    return { data: results.map((r) => r.data) };
  },
  async getManyReference() { return { data: [], total: 0 }; },
};
