// Thin typed client for the backend API.
import type {
  AuditEvent,
  CMADetail,
  CMASummary,
  Comparable,
  Config,
  CSVImportResult,
  Report,
  Sensitivity,
  Strategy,
  Subject,
  Valuation,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, init);
  } catch {
    throw new ApiError(0, "Cannot reach the API server. Is the backend running?");
  }
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail) && body.detail[0]?.msg) {
        detail = body.detail
          .map((d: { loc?: (string | number)[]; msg: string }) =>
            `${(d.loc ?? []).slice(1).join(".")}: ${d.msg}`)
          .join("; ");
      }
    } catch {
      // non-JSON error body; keep the generic message
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

const json = (method: string, body?: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const api = {
  listCmas: () => request<CMASummary[]>("/api/cmas"),
  createCma: (title: string) => request<CMADetail>("/api/cmas", json("POST", { title })),
  getCma: (id: number) => request<CMADetail>(`/api/cmas/${id}`),
  updateCma: (id: number, patch: Partial<Pick<CMADetail, "title" | "status" | "notes">>) =>
    request<CMADetail>(`/api/cmas/${id}`, json("PATCH", patch)),

  saveSubject: (cmaId: number, subject: Omit<Subject, "id">) =>
    request<Subject>(`/api/cmas/${cmaId}/subject`, json("PUT", subject)),

  getConfig: (cmaId: number) => request<Config>(`/api/cmas/${cmaId}/config`),
  updateConfig: (cmaId: number, patch: Partial<Config>) =>
    request<Config>(`/api/cmas/${cmaId}/config`, json("PUT", patch)),

  listComparables: (cmaId: number) =>
    request<Comparable[]>(`/api/cmas/${cmaId}/comparables`),
  addComparable: (cmaId: number, comp: Record<string, unknown>) =>
    request<Comparable>(`/api/cmas/${cmaId}/comparables`, json("POST", comp)),
  updateComparable: (compId: number, patch: Record<string, unknown>) =>
    request<Comparable>(`/api/comparables/${compId}`, json("PATCH", patch)),
  deleteComparable: (compId: number) =>
    request<void>(`/api/comparables/${compId}`, { method: "DELETE" }),
  importCsv: (cmaId: number, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<CSVImportResult>(`/api/cmas/${cmaId}/comparables/import-csv`, {
      method: "POST",
      body: form,
    });
  },
  updateSelection: (
    compId: number,
    patch: { included?: boolean; user_weight_multiplier?: number; exclusion_reason?: string },
  ) => request<Comparable>(`/api/comparables/${compId}/selection`, json("POST", patch)),

  recalcSimilarity: (cmaId: number) =>
    request<Comparable[]>(`/api/cmas/${cmaId}/similarity/recalculate`, { method: "POST" }),
  suggestAdjustments: (cmaId: number) =>
    request<Comparable[]>(`/api/cmas/${cmaId}/adjustments/suggest`, { method: "POST" }),
  addAdjustment: (compId: number, adj: Record<string, unknown>) =>
    request<Comparable["adjustments"][number]>(
      `/api/comparables/${compId}/adjustments`, json("POST", adj)),
  updateAdjustment: (adjId: number, patch: { amount?: number; explanation?: string }) =>
    request<Comparable["adjustments"][number]>(
      `/api/adjustments/${adjId}`, json("PATCH", patch)),
  deleteAdjustment: (adjId: number) =>
    request<void>(`/api/adjustments/${adjId}`, { method: "DELETE" }),

  getValuation: (cmaId: number) => request<Valuation>(`/api/cmas/${cmaId}/valuation`),
  getSensitivity: (cmaId: number) =>
    request<Sensitivity>(`/api/cmas/${cmaId}/sensitivity`),
  recalcValuation: (cmaId: number) =>
    request<Valuation>(`/api/cmas/${cmaId}/valuation/recalculate`, { method: "POST" }),

  listStrategies: (cmaId: number) => request<Strategy[]>(`/api/cmas/${cmaId}/strategies`),
  generateStrategies: (cmaId: number) =>
    request<Strategy[]>(`/api/cmas/${cmaId}/strategies/generate`, { method: "POST" }),
  updateStrategy: (strategyId: number, list_price: number) =>
    request<Strategy>(`/api/strategies/${strategyId}`, json("PATCH", { list_price })),

  listAudit: (cmaId: number) => request<AuditEvent[]>(`/api/cmas/${cmaId}/audit`),

  generateReport: (cmaId: number) =>
    request<Report>(`/api/cmas/${cmaId}/report`, { method: "POST" }),
  listReports: (cmaId: number) => request<Report[]>(`/api/cmas/${cmaId}/reports`),
  reportDownloadUrl: (reportId: number) => `${API_BASE}/api/reports/${reportId}/download`,
  csvTemplateUrl: () => `${API_BASE}/api/csv-template`,
};
