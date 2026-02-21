export type ServiceAUser = {
  id: number;
  email: string;
  username: string;
  is_staff: boolean;
};

export type Project = {
  id: number;
  name: string;
  owner: number;
  created_at: string;
  updated_at: string;
};

export type AnalysisRunStatus = "pending" | "running" | "completed" | "failed";

export type AnalysisRun = {
  id: number;
  project: number;
  status: AnalysisRunStatus;
  current_file_path: string;
  baseline_file_path: string | null;
  cleaning_options: Record<string, unknown>;
  insight_report: unknown | null;
  pdf_file_path: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type CleaningOptions = {
  dropDuplicates?: boolean;
  dropMissing?: boolean;
  capOutliers?: boolean;
  normalizeColumns?: boolean;
};

export type ApiError = {
  status: number;
  bodyText: string;
};

function resolveServiceABaseUrl(): string {
  const fromEnv = (import.meta as any).env?.VITE_SERVICE_A_URL as string | undefined;
  if (fromEnv && typeof fromEnv === "string" && fromEnv.trim()) {
    return fromEnv.replace(/\/$/, "");
  }

  // Default: use same hostname as the frontend page to avoid localhost/127.0.0.1 cookie mismatch.
  const protocol = window.location.protocol === "https:" ? "https:" : "http:";
  const hostname = window.location.hostname || "127.0.0.1";
  return `${protocol}//${hostname}:8002`;
}

const SERVICE_A_BASE_URL = resolveServiceABaseUrl();

let csrfTokenCache: string | null = null;

function isUnsafeMethod(method: string): boolean {
  return !["GET", "HEAD", "OPTIONS"].includes(method.toUpperCase());
}

async function readBodyTextSafe(resp: Response): Promise<string> {
  try {
    return await resp.text();
  } catch {
    return "";
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method || "GET").toUpperCase();

  const headers = new Headers(init.headers || undefined);
  headers.set("Accept", "application/json");

  // Only set JSON Content-Type when body is plain object/string.
  // For FormData uploads, the browser must set the boundary.
  const isFormData = typeof FormData !== "undefined" && init.body instanceof FormData;
  if (!isFormData && init.body != null && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (isUnsafeMethod(method)) {
    const token = await ensureCsrfToken();
    if (token) headers.set("X-CSRFToken", token);
  }

  const resp = await fetch(`${SERVICE_A_BASE_URL}${path}`, {
    ...init,
    method,
    headers,
    credentials: "include",
  });

  if (!resp.ok) {
    const bodyText = await readBodyTextSafe(resp);
    const err: ApiError = { status: resp.status, bodyText };
    throw err;
  }

  // PDF downloads and some endpoints may not be JSON; callers should use specialized helpers.
  const ct = resp.headers.get("content-type") || "";
  if (ct.includes("application/json") || ct.includes("application/vnd.oai.openapi+json")) {
    return (await resp.json()) as T;
  }

  // Fallback: treat as text.
  return (await (resp.text() as unknown)) as T;
}

export async function ensureCsrfToken(): Promise<string | null> {
  if (csrfTokenCache) return csrfTokenCache;
  const data = await request<{ csrfToken: string }>("/api/auth/csrf/", { method: "GET" });
  csrfTokenCache = data.csrfToken;
  return csrfTokenCache;
}

export function clearCsrfTokenCache(): void {
  csrfTokenCache = null;
}

// ----------------------
// Auth
// ----------------------

export async function login(email: string, password: string): Promise<{ user: ServiceAUser; csrfToken?: string }> {
  // Ensure CSRF token exists before login.
  await ensureCsrfToken();

  const data = await request<{ user: ServiceAUser; csrfToken?: string }>("/api/auth/login/", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });

  // Django rotates CSRF on login; store the new value if provided.
  if (data.csrfToken) csrfTokenCache = data.csrfToken;

  return data;
}

export async function logout(): Promise<void> {
  await request<{ success: boolean }>("/api/auth/logout/", { method: "POST" });
  clearCsrfTokenCache();
}

export async function getCurrentUser(): Promise<ServiceAUser> {
  const data = await request<{ user: ServiceAUser }>("/api/auth/me/", { method: "GET" });
  return data.user;
}

// ----------------------
// Projects
// ----------------------

export async function listProjects(): Promise<Project[]> {
  return await request<Project[]>("/api/projects/", { method: "GET" });
}

export async function createProject(name: string): Promise<Project> {
  return await request<Project>("/api/projects/", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

// ----------------------
// Analysis Runs
// ----------------------

export async function startAnalysis(params: {
  projectId: number;
  currentFile: File;
  baselineFile?: File | null;
  cleaningOptions?: CleaningOptions;
  metricSchema?: string | null;
}): Promise<AnalysisRun> {
  const form = new FormData();
  form.append("project_id", String(params.projectId));
  form.append("current_file", params.currentFile, params.currentFile.name);
  if (params.baselineFile) {
    form.append("baseline_file", params.baselineFile, params.baselineFile.name);
  }

  if (params.cleaningOptions && Object.keys(params.cleaningOptions).length > 0) {
    form.append("cleaning_options", JSON.stringify(params.cleaningOptions));
  }

  if (params.metricSchema != null && String(params.metricSchema).trim()) {
    form.append("metric_schema", String(params.metricSchema));
  }

  return await request<AnalysisRun>("/api/analysis-runs/", {
    method: "POST",
    body: form,
  });
}

export async function listAnalysisRuns(): Promise<AnalysisRun[]> {
  return await request<AnalysisRun[]>("/api/analysis-runs/", { method: "GET" });
}

export async function getAnalysisRun(id: number): Promise<AnalysisRun> {
  return await request<AnalysisRun>(`/api/analysis-runs/${id}/`, { method: "GET" });
}

export async function downloadAnalysisPdf(id: number): Promise<Blob> {
  const resp = await fetch(`${SERVICE_A_BASE_URL}/api/analysis-runs/${id}/pdf/`, {
    method: "GET",
    credentials: "include",
  });

  if (!resp.ok) {
    const bodyText = await readBodyTextSafe(resp);
    const err: ApiError = { status: resp.status, bodyText };
    throw err;
  }

  return await resp.blob();
}

export async function pollAnalysisRun(params: {
  id: number;
  intervalMs?: number;
  timeoutMs?: number;
}): Promise<AnalysisRun> {
  const intervalMs = params.intervalMs ?? 1500;
  const timeoutMs = params.timeoutMs ?? 5 * 60 * 1000;

  const started = Date.now();
  while (true) {
    const run = await getAnalysisRun(params.id);
    if (run.status === "completed" || run.status === "failed") return run;

    if (Date.now() - started > timeoutMs) {
      const err: ApiError = { status: 500, bodyText: "Polling timed out" };
      throw err;
    }

    await new Promise((r) => setTimeout(r, intervalMs));
  }
}

export function getServiceABaseUrlForDebug(): string {
  return SERVICE_A_BASE_URL;
}
