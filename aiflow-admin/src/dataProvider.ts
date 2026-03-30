import { DataProvider } from "react-admin";

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
    const allData = (json[config.listKey] || []).map((item: Record<string, unknown>) => ({
      ...item,
      id: item[config.idField] || item.id,
    }));

    // Client-side pagination (API returns all data)
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
