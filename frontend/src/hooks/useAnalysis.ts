import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { analysisApi, projectsApi, AnalysisRun } from "@/lib/api";
import { useActiveWorkspace } from "@/hooks/useWorkspaces";

/** Ensure at least one project exists for the active workspace (client) and return it */
export function useDefaultProject() {
  const { activeWorkspaceId } = useActiveWorkspace();

  return useQuery({
    queryKey: ["projects", "default", activeWorkspaceId],
    queryFn: async () => {
      const projects = await projectsApi.list(activeWorkspaceId);
      if (projects.length > 0) return projects[0];
      return projectsApi.create("Default Project", activeWorkspaceId);
    },
    enabled: activeWorkspaceId !== null,
    staleTime: 30000,
  });
}

/** List all analysis runs for active workspace */
export function useAnalysisRuns() {
  const { activeWorkspaceId } = useActiveWorkspace();

  return useQuery({
    queryKey: ["analysis-runs", activeWorkspaceId],
    queryFn: () => analysisApi.list(activeWorkspaceId),
    enabled: activeWorkspaceId !== null,
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

/** Get the latest completed analysis run for active workspace */
export function useLatestCompletedRun() {
  const { activeWorkspaceId } = useActiveWorkspace();

  return useQuery({
    queryKey: ["analysis-runs", "latest-completed", activeWorkspaceId],
    queryFn: async (): Promise<AnalysisRun | null> => {
      if (!activeWorkspaceId) return null;
      const runs = await analysisApi.list(activeWorkspaceId);
      const completed = runs
        .filter((r) => r.status === "completed")
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
      return completed[0] ?? null;
    },
    enabled: activeWorkspaceId !== null,
  });
}

/** Create a new analysis run */
export function useCreateAnalysis() {
  const qc = useQueryClient();
  const { activeWorkspaceId } = useActiveWorkspace();

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
        activeWorkspaceId
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["analysis-runs"] });
    },
  });
}

/** Delete an analysis run */
export function useDeleteRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => analysisApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["analysis-runs"] });
    },
  });
}
