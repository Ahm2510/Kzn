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
  total_transactions?: number | null;
  products_analyzed?: number | null;
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
      // Distribution niche (Prompt 1): dead / slow-moving stock with rupee value
      dead_stock_skus?: Array<{
        sku: string;
        last_sold: string;
        days_inactive: number;
        value_tied_up: number;
        avg_transaction_value: number;
      }>;
      total_dead_stock_value?: number | null;
      dead_stock_count?: number | null;
      dead_stock_window_days?: number | null;
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
    customer_segmentation?: {
      segments?: Array<{
        segment_label: string;
        segment_basis: string;
        tier: string;
        customer_count: number;
        total_revenue: number;
        revenue_share_pct: number;
        avg_revenue_per_customer: number;
        avg_order_frequency?: number | null;
        avg_recency_days?: number | null;
        period_growth_pct?: number | null;
        concentration_pct: number;
        stability: string;
        confidence: string;
        explanation: string;
        warning?: string | null;
        watchlist?: boolean;
      }>;
      segment_count?: number;
      segment_basis?: string;
      total_customers?: number;
      has_at_risk?: boolean;
      has_declining?: boolean;
      warning?: string | null;
      confidence?: string;
    };
    concentration_risk_dashboard?: {
      dimensions?: Array<{
        dimension: string;
        dimension_column: string;
        contributor_count: number;
        top_1_share_pct: number;
        top_5_share_pct: number;
        top_10_share_pct: number;
        top_20_pct_share: number;
        hhi: number;
        gini: number;
        pareto_ratio: number;
        composite_score: number;
        risk_level: "low" | "moderate" | "high" | "critical";
        top_contributors?: Array<{
          name: string;
          revenue: number;
          share_pct: number;
        }>;
        trend?: string | null;
        hhi_change_pct?: number | null;
        confidence: string;
        explanation: string;
        warning?: string | null;
        watchlist?: boolean;
      }>;
      dimension_count?: number;
      overall_risk?: string;
      overall_score?: number;
      has_critical?: boolean;
      has_high?: boolean;
      warning?: string | null;
      confidence?: string;
    };
    enhanced_executive_summary?: {
      narrative?: string;
      sections?: Array<{
        heading: string;
        content: string;
        sentiment: string;
      }>;
      overall_sentiment?: string;
      confidence?: string;
      key_positives?: string[];
      key_risks?: string[];
      watchpoints?: string[];
      headline_metrics?: string[];      // Prompt 1: top-line rupee figures
      data_coverage?: string;
      warning?: string | null;
    };
    mom_commentary?: {
      period_label?: string;
      revenue_current?: number;
      revenue_baseline?: number | null;
      absolute_change?: number | null;
      percent_change?: number | null;
      direction?: string;
      magnitude?: string;
      is_meaningful?: boolean;
      commentary?: string;
      interpretation?: string;
      driver_hint?: string | null;
      confidence?: string;
      warning?: string | null;
      sample_size?: number;
      has_baseline?: boolean;
    };
    enhanced_products_to_watch?: {
      products?: Array<{
        product: string;
        status: string;
        reason: string;
        revenue: number;
        revenue_share_pct: number;
        transaction_count: number;
        trend_direction?: string | null;
        momentum?: string | null;
        volatility?: string | null;
        confidence: string;
        severity: string;
        action_direction?: string | null;
        warning?: string | null;
      }>;
      product_count?: number;
      total_products_analyzed?: number;
      has_declining?: boolean;
      has_unstable?: boolean;
      confidence?: string;
      warning?: string | null;
    };
    forecast?: {
      forecast_horizon: number;
      granularity: string;
      historical_points: Array<{
        period_label: string;
        projected_value: number;
        lower_bound: number;
        upper_bound: number;
      }>;
      projected_points: Array<{
        period_label: string;
        projected_value: number;
        lower_bound: number;
        upper_bound: number;
      }>;
      trend_direction: string;
      trend_slope: number;
      r_squared: number;
      confidence: string;
      confidence_reason: string;
      explanation: string;
      warning?: string | null;
      revenue_column_used: string;
      date_column_used?: string | null;
      sample_size: number;
    } | null;
    margin_analysis?: {
      total_revenue: number;
      total_cost: number;
      total_gross_profit: number;
      overall_margin_pct: number;
      margin_health: string;              // "healthy"|"moderate"|"thin"|"critical"
      margin_health_explanation: string;
      revenue_column_used: string;
      cost_column_used: string;
      has_product_breakdown: boolean;
      product_breakdown?: Array<{
        product: string;
        revenue: number;
        cost: number;
        gross_profit: number;
        margin_pct: number;
        tier: string;                     // "healthy"|"moderate"|"thin"|"loss_making"
        revenue_share_pct: number;
        watchlist: boolean;
      }> | null;
      products_loss_making: number;
      products_thin_margin: number;
      products_healthy: number;
      baseline_margin_pct?: number | null;
      margin_change_pct?: number | null;
      margin_direction?: string | null;   // "improving"|"stable"|"declining"
      confidence: string;
      confidence_reason: string;
      warning?: string | null;
      sample_size: number;
    } | null;
    cohort_retention?: {
      cohort_table: Array<{
        cohort_label: string;
        cohort_size: number;
        periods: number[];
        period_labels: string[];
      }>;
      summary: {
        overall_retention_rate: number;
        avg_orders_per_customer: number;
        single_purchase_customers_pct: number;
        repeat_purchase_rate: number;
        best_cohort?: string | null;
        worst_cohort?: string | null;
        cohort_trend: string;           // "improving"|"stable"|"declining"
        at_risk_cohorts: string[];
      };
      customer_column_used: string;
      date_column_used: string;
      revenue_column_used: string;
      total_customers: number;
      total_cohorts: number;
      analysis_granularity: string;
      confidence: string;
      confidence_reason: string;
      explanation: string;
      warning?: string | null;
      has_sufficient_history: boolean;
      sample_size: number;
    } | null;
    products_to_watch?: string[];

    // ── Distribution niche (Prompt 1) ──────────────────────────────────────
    customer_churn_risk?: {
      customers?: Array<{
        customer: string;
        risk: "churned" | "at_risk" | "active";
        order_count: number;
        days_since_last_order: number;
        avg_gap_days?: number | null;
        last_order_date?: string | null;
        total_revenue: number;
        revenue_share_pct: number;
        explanation: string;
      }>;
      total_customers?: number;
      at_risk_count?: number;
      churned_count?: number;
      revenue_at_risk?: number;
      revenue_at_risk_pct?: number;
      has_at_risk?: boolean;
      basis?: string;
      confidence?: string;
      warning?: string | null;
      headline_action?: string | null;
    };
    receivables_risk?: {
      customers?: Array<{
        customer: string;
        outstanding: number;
        share_pct: number;
        aging_bucket?: string | null;
        oldest_unpaid_days?: number | null;
        explanation?: string | null;
      }>;
      total_outstanding?: number;
      customer_count?: number;
      aging_available?: boolean;
      over_45_amount?: number;
      over_60_amount?: number;
      over_90_amount?: number;
      over_45_customer_count?: number;
      confidence?: string;
      warning?: string | null;
      headline_action?: string | null;
    };
    action_list?: Array<{
      category: "churn" | "dead_stock" | "receivables" | string;
      priority: number;
      headline: string;
      detail?: string | null;
    }>;
    distribution_schema?: Record<string, { column: string | null; confidence: number; mode: string }>;
    schema_warnings?: string[];

    data_quality?: {
      rows_before?: number;
      rows_after?: number;
      columns_before?: number;
      columns_after?: number;
      columns_renamed?: string[];
      columns_currency_cleaned?: string[];
      date_columns_parsed?: string[];
      null_rows_dropped?: number;
      duplicate_rows_dropped?: number;
      missing_value_summary?: Record<string, { null_count: number; null_pct: number }>;
      schema_detected?: {
        has_revenue?: boolean;
        has_quantity?: boolean;
        has_product?: boolean;
        has_customer?: boolean;
        has_order_id?: boolean;
        has_date?: boolean;
        has_category?: boolean;
        has_sku?: boolean;
        has_price?: boolean;
        has_inventory?: boolean;
        has_country?: boolean;
        detected_columns?: Record<string, string>;
      };
      granularity?: {
        granularity?: string;
        confidence?: string;
        explanation?: string;
      };
      warnings?: string[];
    };
    meta?: Record<string, unknown>;




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

// ── Password Management ──

export interface ChangePasswordPayload {
  old_password: string;
  new_password: string;
}

export interface AdminResetPasswordPayload {
  user_id: number;
  new_password: string;
}

export interface AdminUser {
  id: number;
  username: string;
  email: string;
  is_staff: boolean;
  last_login: string | null;
}

export const passwordApi = {
  changePassword: (payload: ChangePasswordPayload) =>
    api<{ success: boolean }>("/auth/change-password/", { method: "POST", body: payload }),

  adminResetUserPassword: (payload: AdminResetPasswordPayload) =>
    api<{ success: boolean }>("/auth/admin/reset-user-password/", { method: "POST", body: payload }),

  adminListUsers: () =>
    api<AdminUser[]>("/auth/admin/users/"),
};
