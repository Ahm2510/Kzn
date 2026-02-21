import { useEffect, useMemo, useState } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { Button } from "@/components/ui/button";
import { MetricCard } from "@/components/ui/MetricCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { Download, FileText, Clock, Database, Lightbulb } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

import * as serviceA from "@/api/serviceA";

// Types for backend data
interface ReportData {
  title: string;
  generatedAt: string;
  primaryDataset: string;
  comparisonPeriod: string | null;
  insightCount: number;
  reportUrl: string | null;
  version: string;
}

// State type
type ReportState = 
  | { status: "loading" }
  | { status: "empty" }
  | { status: "error"; message: string }
  | { status: "success"; data: ReportData };

export default function Report() {
  const navigate = useNavigate();
  const location = useLocation();

  const runId = useMemo(() => {
    const q = new URLSearchParams(location.search);
    const raw = q.get("id");
    if (!raw) return null;
    const n = Number(raw);
    return Number.isFinite(n) ? n : null;
  }, [location.search]);

  const [pdfUrl, setPdfUrl] = useState<string | null>(null);

  const [state, setState] = useState<ReportState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    if (!runId) {
      setState({ status: "empty" });
      return;
    }

    (async () => {
      setState({ status: "loading" });
      try {
        const run = await serviceA.getAnalysisRun(runId);
        if (cancelled) return;

        if (run.status !== "completed") {
          setState({
            status: "success",
            data: {
              title: `Report for run #${run.id}`,
              generatedAt: new Date(run.updated_at).toLocaleString(),
              primaryDataset: run.current_file_path,
              comparisonPeriod: run.baseline_file_path,
              insightCount: 0,
              reportUrl: null,
              version: "0.1.0",
            },
          });
          return;
        }

        const report = run.insight_report as any;
        const insightCount = Array.isArray(report?.insights) ? report.insights.length : 0;

        setState({
          status: "success",
          data: {
            title: `Report for run #${run.id}`,
            generatedAt: new Date(run.updated_at).toLocaleString(),
            primaryDataset: run.current_file_path,
            comparisonPeriod: run.baseline_file_path,
            insightCount,
            reportUrl: null,
            version: "0.1.0",
          },
        });
      } catch (e) {
        if (cancelled) return;
        const err = e as { status?: number };
        if (err?.status === 404) {
          setState({ status: "empty" });
        } else if (err?.status === 403) {
          setState({ status: "error", message: "Not authenticated. Please login again." });
        } else {
          setState({ status: "error", message: "Unable to load report." });
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [runId]);

  useEffect(() => {
    return () => {
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    };
  }, [pdfUrl]);

  const handleDownload = async () => {
    if (!runId) return;
    const blob = await serviceA.downloadAnalysisPdf(runId);
    const url = URL.createObjectURL(blob);
    setPdfUrl(url);
    window.open(url, "_blank");
  };

  // Loading state
  if (state.status === "loading") {
    return (
      <AppLayout>
        <div className="page-container animate-fade-in">
          <div className="max-w-4xl">
            <section className="section-spacing">
              <div className="flex items-start justify-between gap-6">
                <div>
                  <Skeleton className="h-10 w-80 mb-3" />
                  <Skeleton className="h-5 w-64" />
                </div>
                <Skeleton className="h-11 w-36" />
              </div>
            </section>

            <section className="section-spacing">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Skeleton className="h-24 rounded-lg" />
                <Skeleton className="h-24 rounded-lg" />
                <Skeleton className="h-24 rounded-lg" />
              </div>
            </section>

            <section className="section-spacing">
              <Skeleton className="h-[500px] w-full rounded-lg" />
            </section>
          </div>
        </div>
      </AppLayout>
    );
  }

  // Error state
  if (state.status === "error") {
    return (
      <AppLayout>
        <EmptyState
          icon={FileText}
          title="Unable to load report"
          description={state.message || "An error occurred while loading the report."}
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

  // Empty state - no report generated
  if (state.status === "empty") {
    return (
      <AppLayout>
        <EmptyState
          icon={FileText}
          title="No report generated"
          description="Generate insights from your dataset first, then create an executive report."
          action={
            <Button onClick={() => navigate("/insights")}>
              <Lightbulb className="w-4 h-4 mr-2" />
              View insights
            </Button>
          }
          className="h-[calc(100vh-3.5rem)]"
        />
      </AppLayout>
    );
  }

  // Success state
  const { data } = state;

  return (
    <AppLayout>
      <div className="page-container animate-fade-in">
        <div className="max-w-4xl">
          {/* Report header */}
          <section className="section-spacing">
            <div className="flex items-start justify-between gap-6">
              <div>
                <h2 className="font-display text-2xl lg:text-3xl font-semibold text-foreground mb-3">
                  {data.title}
                </h2>
                <p className="text-muted-foreground">
                  Generated {data.generatedAt}
                </p>
              </div>
              <Button 
                className="font-medium h-11"
                disabled={!runId}
                onClick={handleDownload}
              >
                <Download className="w-4 h-4 mr-2" />
                Download PDF
              </Button>
            </div>
          </section>

          {/* Report metadata */}
          <section className="section-spacing">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <MetricCard
                label="Primary dataset"
                value={data.primaryDataset}
              />
              {data.comparisonPeriod && (
                <MetricCard
                  label="Comparison period"
                  value={data.comparisonPeriod}
                />
              )}
              <MetricCard
                label="Insights included"
                value={data.insightCount.toString()}
              />
            </div>
          </section>

          {/* PDF Preview placeholder */}
          {pdfUrl ? (
            <section className="section-spacing">
              <div className="bg-card border border-border rounded-lg overflow-hidden shadow-sm">
                <div className="bg-muted/20 border-b border-border px-6 py-4 flex items-center gap-3">
                  <FileText className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground font-mono">
                    Report Preview
                  </span>
                </div>
                <div className="p-10 lg:p-14 bg-background min-h-[400px] flex items-center justify-center">
                  <div className="text-center">
                    <FileText className="w-12 h-12 text-muted-foreground/40 mx-auto mb-4" />
                    <p className="text-muted-foreground">
                      Report preview will be displayed here
                    </p>
                    <Button 
                      variant="outline" 
                      className="mt-4"
                      onClick={() => window.open(pdfUrl, "_blank")}
                    >
                      Open full report
                    </Button>
                  </div>
                </div>
              </div>
            </section>
          ) : (
            <section className="section-spacing">
              <div className="bg-muted/30 border border-border rounded-lg p-10 text-center">
                <FileText className="w-12 h-12 text-muted-foreground/40 mx-auto mb-4" />
                <p className="text-muted-foreground">
                  Report is not available yet. If this analysis is still running, check back soon.
                </p>
              </div>
            </section>
          )}

          {/* Version info */}
          <section>
            <div className="flex items-center gap-8 text-sm text-muted-foreground/70">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4" />
                <span>Generated {data.generatedAt}</span>
              </div>
              <div className="flex items-center gap-2">
                <Database className="w-4 h-4" />
                <span>Version {data.version}</span>
              </div>
            </div>
          </section>
        </div>
      </div>
    </AppLayout>
  );
}
