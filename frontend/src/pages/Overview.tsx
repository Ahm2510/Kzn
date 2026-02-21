import { useEffect, useMemo, useState } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Database, LayoutDashboard } from "lucide-react";
import { useNavigate } from "react-router-dom";

import * as serviceA from "@/api/serviceA";

type OverviewState =
  | { status: "loading" }
  | { status: "empty" }
  | { status: "error"; message: string }
  | {
      status: "success";
      data: {
        projects: Array<{ id: number; name: string; createdAt: string; analysisCount: number }>;
        recentRuns: Array<{
          id: number;
          projectName: string;
          status: "pending" | "processing" | "complete" | "error";
          createdAt: string;
          hasPdf: boolean;
        }>;
      };
    };

export default function Overview() {
  const navigate = useNavigate();
  const [state, setState] = useState<OverviewState>({ status: "loading" });

  const statusFromRun = useMemo(() => {
    return (run: serviceA.AnalysisRun): "pending" | "processing" | "complete" | "error" => {
      if (run.status === "completed") return "complete";
      if (run.status === "failed") return "error";
      if (run.status === "running") return "processing";
      return "pending";
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setState({ status: "loading" });
      try {
        const [projects, runs] = await Promise.all([
          serviceA.listProjects(),
          serviceA.listAnalysisRuns(),
        ]);

        if (cancelled) return;

        if (projects.length === 0 && runs.length === 0) {
          setState({ status: "empty" });
          return;
        }

        const runsByProjectId = new Map<number, number>();
        for (const r of runs) {
          runsByProjectId.set(r.project, (runsByProjectId.get(r.project) ?? 0) + 1);
        }

        const projectNameById = new Map<number, string>();
        for (const p of projects) projectNameById.set(p.id, p.name);

        const projectsView = projects
          .map((p) => ({
            id: p.id,
            name: p.name,
            createdAt: new Date(p.created_at).toLocaleString(),
            analysisCount: runsByProjectId.get(p.id) ?? 0,
          }))
          .sort((a, b) => b.id - a.id);

        const recentRuns = [...runs]
          .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
          .slice(0, 8)
          .map((r) => ({
            id: r.id,
            projectName: projectNameById.get(r.project) ?? `Project #${r.project}`,
            status: statusFromRun(r),
            createdAt: new Date(r.created_at).toLocaleString(),
            hasPdf: !!r.pdf_file_path,
          }));

        setState({
          status: "success",
          data: {
            projects: projectsView,
            recentRuns,
          },
        });
      } catch (e) {
        if (cancelled) return;
        const err = e as { status?: number };
        if (err?.status === 403) {
          setState({ status: "error", message: "Not authenticated. Please login again." });
        } else {
          setState({ status: "error", message: "Unable to load overview." });
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [statusFromRun]);

  // Loading state
  if (state.status === "loading") {
    return (
      <AppLayout>
        <div className="page-container animate-fade-in">
          <section className="section-spacing">
            <Skeleton className="h-6 w-48 mb-6" />
            <Skeleton className="h-32 w-full rounded-lg mb-8" />
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Skeleton className="h-20 rounded-lg" />
              <Skeleton className="h-20 rounded-lg" />
              <Skeleton className="h-20 rounded-lg" />
              <Skeleton className="h-20 rounded-lg" />
            </div>
          </section>
        </div>
      </AppLayout>
    );
  }

  // Error state
  if (state.status === "error") {
    return (
      <AppLayout>
        <EmptyState
          icon={LayoutDashboard}
          title="Unable to load overview"
          description={state.message || "An error occurred while loading the analysis overview."}
          action={
            <Button variant="outline" onClick={() => window.location.reload()}>
              Try again
            </Button>
          }
          className="h-[calc(100vh-3.5rem)]"
        />
      </AppLayout>
    );
  }

  // Empty state
  if (state.status === "empty") {
    return (
      <AppLayout>
        <EmptyState
          icon={Database}
          title="No active analysis"
          description="Upload a dataset to begin generating insights."
          action={
            <Button onClick={() => navigate("/datasets")}>
              <Database className="w-4 h-4 mr-2" />
              Upload dataset
            </Button>
          }
          className="h-[calc(100vh-3.5rem)]"
        />
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="page-container animate-fade-in">
        {state.status === "success" && (
          <>
            <section className="section-spacing">
              <div className="flex items-center justify-between gap-4 mb-4">
                <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
                  Projects
                </h3>
                <Button variant="outline" onClick={() => navigate("/datasets")}>New analysis</Button>
              </div>
              <div className="bg-card border border-border rounded-lg overflow-hidden">
                <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-border text-xs font-mono text-muted-foreground">
                  <div className="col-span-6">Name</div>
                  <div className="col-span-4">Created</div>
                  <div className="col-span-2 text-right">Analyses</div>
                </div>
                <div className="divide-y divide-border">
                  {state.data.projects.map((p) => (
                    <div key={p.id} className="grid grid-cols-12 gap-4 px-6 py-4 text-sm">
                      <div className="col-span-6 font-medium text-foreground truncate" title={p.name}>{p.name}</div>
                      <div className="col-span-4 text-muted-foreground">{p.createdAt}</div>
                      <div className="col-span-2 text-right font-mono text-foreground">{p.analysisCount}</div>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            <section className="section-spacing">
              <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider mb-4">
                Recent analysis runs
              </h3>
              <div className="bg-card border border-border rounded-lg overflow-hidden">
                <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-border text-xs font-mono text-muted-foreground">
                  <div className="col-span-4">Project</div>
                  <div className="col-span-3">Status</div>
                  <div className="col-span-3">Created</div>
                  <div className="col-span-2 text-right">PDF</div>
                </div>
                <div className="divide-y divide-border">
                  {state.data.recentRuns.map((r) => (
                    <div key={r.id} className="grid grid-cols-12 gap-4 px-6 py-4 text-sm items-center">
                      <div className="col-span-4 text-foreground truncate" title={r.projectName}>{r.projectName}</div>
                      <div className="col-span-3">
                        <StatusBadge status={r.status} />
                      </div>
                      <div className="col-span-3 text-muted-foreground">{r.createdAt}</div>
                      <div className="col-span-2 text-right">
                        {r.hasPdf ? (
                          <Button variant="outline" size="sm" onClick={() => navigate(`/report?id=${r.id}`)}>
                            View
                          </Button>
                        ) : (
                          <span className="text-xs text-muted-foreground font-mono">—</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          </>
        )}
      </div>
    </AppLayout>
  );
}
