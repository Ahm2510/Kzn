import { useState, useEffect, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { workspacesApi, Workspace } from "@/lib/api";

const STORAGE_KEY = "kaizen_active_workspace_id";

export function useWorkspaces() {
  return useQuery({
    queryKey: ["workspaces"],
    queryFn: workspacesApi.list,
  });
}

export function useActiveWorkspace() {
  const qc = useQueryClient();
  const { data: workspaces = [], isLoading } = useWorkspaces();
  
  const [activeWorkspaceId, setActiveWorkspaceIdState] = useState<number | null>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? Number(saved) : null;
  });

  // Ensure activeWorkspaceId is valid and synced with fetched workspaces
  useEffect(() => {
    if (workspaces.length === 0) return;
    
    const exists = workspaces.some((w) => w.id === activeWorkspaceId);
    if (!exists || activeWorkspaceId === null) {
      const firstId = workspaces[0].id;
      setActiveWorkspaceIdState(firstId);
      localStorage.setItem(STORAGE_KEY, String(firstId));
    }
  }, [workspaces, activeWorkspaceId]);

  const setActiveWorkspaceId = useCallback(
    (id: number) => {
      setActiveWorkspaceIdState(id);
      localStorage.setItem(STORAGE_KEY, String(id));
      // Invalidate all workspace-scoped query data
      qc.invalidateQueries({ queryKey: ["projects"] });
      qc.invalidateQueries({ queryKey: ["analysis-runs"] });
    },
    [qc]
  );

  const activeWorkspace = workspaces.find((w) => w.id === activeWorkspaceId) ?? workspaces[0] ?? null;

  return {
    workspaces,
    activeWorkspace,
    activeWorkspaceId: activeWorkspace?.id ?? null,
    setActiveWorkspaceId,
    isLoading,
  };
}

export function useCreateWorkspace() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, firmName }: { name: string; firmName?: string }) =>
      workspacesApi.create(name, firmName),
    onSuccess: (newWorkspace) => {
      qc.invalidateQueries({ queryKey: ["workspaces"] });
      localStorage.setItem(STORAGE_KEY, String(newWorkspace.id));
      qc.invalidateQueries({ queryKey: ["projects"] });
      qc.invalidateQueries({ queryKey: ["analysis-runs"] });
    },
  });
}

export function useUpdateWorkspace() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Workspace> }) =>
      workspacesApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["workspaces"] });
    },
  });
}
