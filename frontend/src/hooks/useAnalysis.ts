import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { analysisApi, projectsApi, AnalysisRun } from "@/lib/api";

/** Ensure at least one project exists and return its ID */
export function useDefaultProject() {
  return useQuery({
    queryKey: ["projects", "default"],
    queryFn: async () => {
      const projects = await projectsApi.list();
      if (projects.length > 0) return projects[0];
      return projectsApi.create("Default Project");
    },
    staleTime: Infinity,
  });
}

/** List all analysis runs */
export function useAnalysisRuns() {
  return useQuery({
    queryKey: ["analysis-runs"],
    queryFn: analysisApi.list,
  });
}

/** Get a single analysis run, with polling while pending/running */
export function useAnalysisRun(id: number | null) {
  return useQuery({
    queryKey: ["analysis-runs", id],
    queryFn: () => analysisApi.get(id!),
    enabled: id !== null,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "pending" || status === "running") return 3000;
      return false;
    },
  });
}

/** Get the latest completed analysis run */
export function useLatestCompletedRun() {
  return useQuery({
    queryKey: ["analysis-runs", "latest-completed"],
    queryFn: async (): Promise<AnalysisRun | null> => {
      const runs = await analysisApi.list();
      const completed = runs
        .filter((r) => r.status === "completed")
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
      return completed[0] ?? null;
    },
  });
}

/** Create a new analysis run */
export function useCreateAnalysis() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (params: {
      projectId: number;
      currentFile: File;
      baselineFile?: File | null;
      cleaningOptions?: Record<string, boolean>;
      metricSchema?: string;
    }) =>
      analysisApi.create(
        params.projectId,
        params.currentFile,
        params.baselineFile,
        params.cleaningOptions,
        params.metricSchema,
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["analysis-runs"] });
    },
  });
}
