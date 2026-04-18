/**
 * API client for Django service_a.
 * Handles CSRF tokens, session cookies, and typed requests.
 */

const BASE_URL = "/api"

let csrfToken: string | null = null;

async function fetchCsrfToken(): Promise<string> {
  const res = await fetch(`${BASE_URL}/auth/csrf/`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error("Failed to fetch CSRF token");
  const data = await res.json();
  csrfToken = data.csrfToken;
  return csrfToken!;
}

async function getCsrfToken(): Promise<string> {
  if (csrfToken) return csrfToken;
  return fetchCsrfToken();
}

export function clearCsrfToken() {
  csrfToken = null;
}

export function setCsrfToken(token: string) {
  csrfToken = token;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  formData?: FormData;
}

export async function api<T = unknown>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, formData } = opts;

  const headers: Record<string, string> = {};

  if (method !== "GET" && method !== "HEAD") {
    const token = await getCsrfToken();
    headers["X-CSRFToken"] = token;
  }

  if (body && !formData) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    credentials: "include",
    body: formData ?? (body ? JSON.stringify(body) : undefined),
  });

  if (res.status === 204) return undefined as T;

  if (!res.ok) {
    let errorMsg = `Request failed: ${res.status}`;
    try {
      const errData = await res.json();
      errorMsg = errData.error || errData.detail || errorMsg;
    } catch {
      // ignore parse error
    }
    throw new Error(errorMsg);
  }

  // Handle binary responses (PDF)
  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/pdf")) {
    return (await res.blob()) as T;
  }

  return res.json();
}

// ── Auth ──

export interface DjangoUser {
  id: number;
  email: string;
  username: string;
  is_staff: boolean;
}

export interface LoginResponse {
  user: DjangoUser;
  csrfToken: string;
}

export const authApi = {
  login: (email: string, password: string) =>
    api<LoginResponse>("/auth/login/", { method: "POST", body: { email, password } }),

  logout: () => api("/auth/logout/", { method: "POST" }),

  me: () => api<{ user: DjangoUser }>("/auth/me/"),
};

// ── Projects ──

export interface Project {
  id: number;
  name: string;
  owner: number;
  created_at: string;
  updated_at: string;
}

export const projectsApi = {
  list: () => api<Project[]>("/projects/"),
  create: (name: string) => api<Project>("/projects/", { method: "POST", body: { name } }),
  get: (id: number) => api<Project>(`/projects/${id}/`),
  delete: (id: number) => api(`/projects/${id}/`, { method: "DELETE" }),
};

// ── Analysis Runs ──

export interface AnalysisRun {
  id: number;
  project: number;
  status: "pending" | "running" | "completed" | "failed";
  current_file_path: string | null;
  baseline_file_path: string | null;
  cleaning_options: Record<string, boolean>;
  insight_report: InsightReport | null;
  pdf_file_path: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface InsightReport {
  summary?: string;
  executive_summary?: string;
  trend_direction?: string;
  stability?: string;
  efficiency_signal?: string;
  concentration_risk?: string;
  business_insights?: {
    executive_takeaways?: string[];
    scope?: {
      analyzed?: string[];
      not_analyzed?: string[];
    };
    trend?: {
      direction?: string;
      description?: string;
      confidence?: string;
      driver?: string;
      implication?: string;
      action_direction?: string;
      confidence_basis?: string;
    };
    stability?: {
      category?: string;
      coefficient_of_variation?: number;
      description?: string;
      driver?: string;
      implication?: string;
      action_direction?: string;
      confidence?: string;
      confidence_basis?: string;
    };
    efficiency?: {
      signal?: string;
      description?: string;
      change_percent?: number;
      driver?: string;
      implication?: string;
      action_direction?: string;
      confidence?: string;
      confidence_basis?: string;
    };
    concentration?: {
      top_10_percent_contribution?: number;
      risk_level?: string;
      description?: string;
      driver?: string;
      implication?: string;
      action_direction?: string;
      confidence?: string;
      confidence_basis?: string;
    };
    executive_summary?: string;
    revenue_stability_index?: {
      score: number;
      label: string;
      confidence: string;
      explanation: string;
      contributing_factors?: string[];
      warning?: string;
      coefficient_of_variation?: number;
      spike_ratio?: number;
      has_baseline_comparison?: boolean;
    };
    inventory_health_score?: {
      score: number;
      label: string;
      confidence: string;
      confidence_reason?: string;
      explanation: string;
      contributing_factors?: string[];
      warning?: string;
      data_source?: string;
      has_product_data?: boolean;
      has_quantity_data?: boolean;
      has_stock_data?: boolean;
      watchlist?: string[];
    };
    early_warning_alerts?: {
      alerts?: Array<{
        alert_code: string;
        severity: "critical" | "high" | "medium" | "low";
        title: string;
        description: string;
        driver?: string;
        implication?: string;
        action_direction?: string;
        confidence?: string;
        confidence_basis?: string;
        metric_ref?: string;
      }>;
      alert_count?: number;
      has_critical?: boolean;
      has_high?: boolean;
    };
    cohort_product_performance?: {
      cohorts?: Array<{
        cohort_label: string;
        cohort_basis: string;
        product_count: number;
        transaction_count: number;
        total_revenue: number;
        revenue_share_pct: number;
        avg_revenue_per_product: number;
        period_growth_pct?: number | null;
        stability: string;
        performance_tier: string;
        confidence: string;
        explanation: string;
        warning?: string | null;
        watchlist?: boolean;
      }>;
      cohort_count?: number;
      cohort_basis?: string;
      has_declining?: boolean;
      has_underperformer?: boolean;
      warning?: string | null;
      confidence?: string;
    };
    products_to_watch?: string[];
    meta?: Record<string, any>;

  };
  insights?: Array<{
    code?: string;
    title: string;
    description: string;
    affected_metric?: string;
    driver?: string;
    implication?: string;
    action_direction?: string;
    confidence?: string;
    confidence_basis?: string;
    severity: "high" | "medium" | "low";
  }>;
  comparison?: {
    metric_name: string;
    current_value: string;
    baseline_value: string;
    absolute_change: string;
    percent_change: string;
  } | null;
}

export const analysisApi = {
  list: () => api<AnalysisRun[]>("/analysis-runs/"),

  get: (id: number) => api<AnalysisRun>(`/analysis-runs/${id}/`),

  create: (projectId: number, currentFile: File, baselineFile?: File | null, cleaningOptions?: Record<string, boolean>, metricSchema?: string) => {
    const fd = new FormData();
    fd.append("project_id", String(projectId));
    fd.append("current_file", currentFile);
    if (baselineFile) fd.append("baseline_file", baselineFile);
    if (cleaningOptions) fd.append("cleaning_options", JSON.stringify(cleaningOptions));
    if (metricSchema) fd.append("metric_schema", metricSchema);
    return api<AnalysisRun>("/analysis-runs/", { method: "POST", formData: fd });
  },

  delete: (id: number) => api(`/analysis-runs/${id}/`, { method: "DELETE" }),

  downloadPdf: (id: number) => api<Blob>(`/analysis-runs/${id}/pdf/`),
};
