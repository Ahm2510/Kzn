import { useEffect, useMemo, useState } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { InsightCard, InsightSeverity } from "@/components/ui/InsightCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Lightbulb, Database } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

import * as serviceA from "@/api/serviceA";

// Types matching Django service_a response — checklist §7
interface Insight {
  id: string;
  title: string;
  description: string;
  driver: string;
  implication: string;
  actionDirection: string;
  confidence: string;
  confidenceBasis: string;
  severity: InsightSeverity;
}

type InsightReport = {
  summary?: string;
  insights?: any[];
  business_insights?: any;
  metric_delta?: any;
  metric_deltas?: any[];
};

type InsightsState =
  | { status: "loading" }
  | { status: "empty" }
  | { status: "error"; message: string }
  | {
      status: "success";
      data: {
        runId: number;
        runStatus: serviceA.AnalysisRunStatus;
        hasPdf: boolean;
        summary: string | null;
        insights: Insight[];
        businessInsights: any | null;
      };
    };

export default function Insights() {
  const navigate = useNavigate();
  const location = useLocation();

  const runId = useMemo(() => {
    const q = new URLSearchParams(location.search);
    const raw = q.get("id");
    if (!raw) return null;
    const n = Number(raw);
    return Number.isFinite(n) ? n : null;
  }, [location.search]);

  const [state, setState] = useState<InsightsState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    let intervalId: number | null = null;

    const severityFromAny = (value: any): InsightSeverity => {
      const v = String(value ?? "").toLowerCase();
      if (v === "high" || v === "critical") return "high";
      if (v === "medium" || v === "moderate") return "medium";
      return "low";
    };

    const mapInsight = (ins: any, idx: number): Insight => {
      const title = String(ins?.title ?? ins?.name ?? `Insight ${idx + 1}`);
      const description = String(ins?.description ?? ins?.summary ?? ins?.detail ?? "");
      return {
        id: String(ins?.id ?? idx),
        title,
        description,
        driver: String(ins?.driver ?? ins?.root_cause ?? ""),
        implication: String(ins?.implication ?? ins?.impact ?? ""),
        actionDirection: String(ins?.action_direction ?? ins?.recommendation ?? ""),
        confidence: String(ins?.confidence ?? ins?.confidence_level ?? ""),
        confidenceBasis: String(ins?.confidence_basis ?? ins?.evidence ?? ""),
        severity: severityFromAny(ins?.severity),
      };
    };

    const fetchRun = async () => {
      if (!runId) {
        setState({ status: "empty" });
        return;
      }

      try {
        const run = await serviceA.getAnalysisRun(runId);
        if (cancelled) return;

        const report = (run.insight_report ?? null) as InsightReport | null;
        const insightsArr = Array.isArray(report?.insights) ? report?.insights : [];
        const summary = typeof report?.summary === "string" ? report.summary : null;
        const businessInsights = report?.business_insights ?? null;

        setState({
          status: "success",
          data: {
            runId: run.id,
            runStatus: run.status,
            hasPdf: !!run.pdf_file_path,
            summary,
            insights: insightsArr.map(mapInsight),
            businessInsights,
          },
        });

        if (run.status === "pending" || run.status === "running") {
          if (intervalId == null) {
            intervalId = window.setInterval(fetchRun, 7000);
          }
        } else if (intervalId != null) {
          window.clearInterval(intervalId);
          intervalId = null;
        }
      } catch (e) {
        if (cancelled) return;
        const err = e as { status?: number };
        if (err?.status === 404) {
          setState({ status: "empty" });
        } else if (err?.status === 403) {
          setState({ status: "error", message: "Not authenticated. Please login again." });
        } else {
          setState({ status: "error", message: "Unable to load insights." });
        }
      }
    };

    fetchRun();

    return () => {
      cancelled = true;
      if (intervalId != null) window.clearInterval(intervalId);
    };
  }, [runId]);

  // Loading state
  if (state.status === "loading") {
    return (
      <AppLayout>
        <div className="page-container animate-fade-in">
          <section className="section-spacing">
            <Skeleton className="h-4 w-32 mb-6" />
            <div className="space-y-4">
              <Skeleton className="h-40 w-full rounded-lg" />
              <Skeleton className="h-40 w-full rounded-lg" />
              <Skeleton className="h-40 w-full rounded-lg" />
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
          icon={Lightbulb}
          title="Unable to load insights"
          description={state.message || "An error occurred while loading insights."}
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
          icon={Lightbulb}
          title="No insights generated"
          description="Upload and analyze a dataset to generate insights."
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

  const { data } = state;
  const runStatusBadge =
    data.runStatus === "completed"
      ? "complete"
      : data.runStatus === "failed"
        ? "error"
        : data.runStatus === "running"
          ? "processing"
          : "pending";

  const pdfUrl = `${serviceA.getServiceABaseUrlForDebug()}/api/analysis-runs/${data.runId}/pdf/`;

  return (
    <AppLayout>
      <div className="page-container animate-fade-in">
        <section className="section-spacing">
          <div className="flex items-center justify-between gap-4 mb-6">
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground font-mono">
                Run #{data.runId}
              </p>
              <p className="text-sm text-muted-foreground font-mono">
                {data.insights.length} insight{data.insights.length !== 1 ? "s" : ""} generated
              </p>
            </div>
            <StatusBadge status={runStatusBadge} />
          </div>

          {data.summary && (
            <div className="bg-card border border-border rounded-lg p-6 mb-6">
              <p className="text-xs font-mono text-muted-foreground uppercase tracking-wider mb-3">
                Executive Summary
              </p>
              <p className="text-foreground leading-reading text-base">{data.summary}</p>
            </div>
          )}

          {data.runStatus === "completed" && data.hasPdf && (
            <div className="mb-6">
              <Button onClick={() => window.open(pdfUrl, "_blank")}>
                View PDF Report
              </Button>
            </div>
          )}

          {data.businessInsights && (
            <div className="bg-card border border-border rounded-lg p-6 mb-6">
              <p className="text-xs font-mono text-muted-foreground uppercase tracking-wider mb-3">
                Business Insights
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                {data.businessInsights.trend != null && (
                  <div>
                    <span className="text-muted-foreground">Trend: </span>
                    <span className="text-foreground">{String(data.businessInsights.trend)}</span>
                  </div>
                )}
                {data.businessInsights.stability != null && (
                  <div>
                    <span className="text-muted-foreground">Stability: </span>
                    <span className="text-foreground">{String(data.businessInsights.stability)}</span>
                  </div>
                )}
                {data.businessInsights.efficiency != null && (
                  <div>
                    <span className="text-muted-foreground">Efficiency: </span>
                    <span className="text-foreground">{String(data.businessInsights.efficiency)}</span>
                  </div>
                )}
                {data.businessInsights.concentration != null && (
                  <div>
                    <span className="text-muted-foreground">Concentration: </span>
                    <span className="text-foreground">{String(data.businessInsights.concentration)}</span>
                  </div>
                )}
              </div>

              {Array.isArray(data.businessInsights.executive_takeaways) && (
                <div className="mt-4">
                  <p className="text-xs font-mono text-muted-foreground uppercase tracking-wider mb-2">
                    Executive takeaways
                  </p>
                  <div className="space-y-1 text-sm text-foreground">
                    {data.businessInsights.executive_takeaways.map((t: any, i: number) => (
                      <div key={i}>{String(t)}</div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="space-y-4">
            {data.insights.map((insight) => (
              <InsightCard
                key={insight.id}
                title={insight.title}
                description={insight.description}
                driver={insight.driver}
                implication={insight.implication}
                actionDirection={insight.actionDirection}
                confidence={insight.confidence}
                confidenceBasis={insight.confidenceBasis}
                severity={insight.severity}
              />
            ))}
          </div>
        </section>
      </div>
    </AppLayout>
  );
}
