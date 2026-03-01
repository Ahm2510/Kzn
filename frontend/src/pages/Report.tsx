import { AppLayout } from "@/components/layout/AppLayout";
import { Button } from "@/components/ui/button";
import { MetricCard } from "@/components/ui/MetricCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { Download, FileText, Clock, Database, Lightbulb } from "lucide-react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useLatestCompletedRun, useAnalysisRun } from "@/hooks/useAnalysis";
import { analysisApi } from "@/lib/api";

export default function Report() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const runIdParam = searchParams.get("id");

  // If an ID is provided via query string, show that run; otherwise show the latest
  const { data: specificRun, isLoading: loadingSpecific } = useAnalysisRun(
    runIdParam ? Number(runIdParam) : null,
  );
  const { data: latestRun, isLoading: loadingLatest } = useLatestCompletedRun();

  const run = runIdParam ? specificRun : latestRun;
  const isLoading = runIdParam ? loadingSpecific : loadingLatest;

  const handleDownloadPdf = async () => {
    if (!run) return;
    try {
      const blob = await analysisApi.downloadPdf(run.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `analysis_report_${run.id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // TODO: toast error
    }
  };

  if (isLoading) {
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
          </div>
        </div>
      </AppLayout>
    );
  }

  if (!run || run.status !== "completed") {
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

  const hasPdf = !!run.pdf_file_path;
  const insightCount = run.insight_report?.insights?.length ?? 0;
  const generatedAt = new Date(run.created_at).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <AppLayout>
      <div className="page-container animate-fade-in">
        <div className="max-w-4xl">
          <section className="section-spacing">
            <div className="flex items-start justify-between gap-6">
              <div>
                <h2 className="font-display text-2xl lg:text-3xl font-semibold text-foreground mb-3">
                  Analysis Report #{run.id}
                </h2>
                <p className="text-muted-foreground">Generated {generatedAt}</p>
              </div>
              <Button className="font-medium h-11" disabled={!hasPdf} onClick={handleDownloadPdf}>
                <Download className="w-4 h-4 mr-2" />
                Download PDF
              </Button>
            </div>
          </section>

          <section className="section-spacing">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <MetricCard label="Status" value={run.status} />
              <MetricCard label="Insights" value={String(insightCount)} />
              <MetricCard label="Comparison" value={run.baseline_file_path ? "Yes" : "N/A"} />
            </div>
          </section>

          {hasPdf ? (
            <section className="section-spacing">
              <div className="bg-card border border-border rounded-lg overflow-hidden shadow-sm">
                <div className="bg-muted/20 border-b border-border px-6 py-4 flex items-center gap-3">
                  <FileText className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground font-mono">Report Preview</span>
                </div>
                <div className="p-10 lg:p-14 bg-background min-h-[400px] flex items-center justify-center">
                  <div className="text-center">
                    <FileText className="w-12 h-12 text-muted-foreground/40 mx-auto mb-4" />
                    <p className="text-muted-foreground">PDF report is ready for download</p>
                    <Button variant="outline" className="mt-4" onClick={handleDownloadPdf}>
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
                <p className="text-muted-foreground">PDF report not available for this analysis.</p>
              </div>
            </section>
          )}

          <section>
            <div className="flex items-center gap-8 text-sm text-muted-foreground/70">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4" />
                <span>Generated {generatedAt}</span>
              </div>
              <div className="flex items-center gap-2">
                <Database className="w-4 h-4" />
                <span>Run #{run.id}</span>
              </div>
            </div>
          </section>
        </div>
      </div>
    </AppLayout>
  );
}
