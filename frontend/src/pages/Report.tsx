import { AppLayout } from "@/components/layout/AppLayout";
import { Button } from "@/components/ui/button";
import { MetricCard } from "@/components/ui/MetricCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { InsightCard, InsightSeverity } from "@/components/ui/InsightCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import {
  Download,
  FileText,
  Clock,
  Database,
  Lightbulb,
  Printer,
  ShieldAlert,
  Sparkles,
  AlertTriangle,
  TrendingUp,
  Activity,
  Award,
  Zap,
} from "lucide-react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useLatestCompletedRun, useAnalysisRun } from "@/hooks/useAnalysis";
import { analysisApi } from "@/lib/api";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

export default function Report() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const runIdParam = searchParams.get("id");

  // If an ID is provided via query string, show that run; otherwise show the latest
  const { data: specificRun, isLoading: loadingSpecific } = useAnalysisRun(
    runIdParam ? Number(runIdParam) : null
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
      toast.success("PDF report downloaded successfully.");
    } catch (err: unknown) {
      const error = err as Error;
      toast.error(error.message || "Failed to download PDF report. Ensure backend PDF generator is running.");
    }
  };

  const handlePrint = () => {
    window.print();
  };

  if (isLoading) {
    return (
      <AppLayout>
        <div className="page-container animate-fade-in">
          <div className="max-w-4xl mx-auto">
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
              <Skeleton className="h-56 w-full rounded-lg" />
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
          description="Generate insights from your dataset first, then compile an executive report."
          action={
            <Button onClick={() => navigate("/insights")} className="bg-primary text-primary-foreground hover:bg-primary/95">
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

  const bi = run.insight_report?.business_insights;
  const rsi = bi?.revenue_stability_index;
  const ihs = bi?.inventory_health_score;
  const alerts = bi?.early_warning_alerts;

  return (
    <AppLayout>
      <div className="page-container animate-fade-in">
        <div className="max-w-4xl mx-auto space-y-8 print:p-0">
          {/* Executive Header Controls */}
          <section className="border-b border-border pb-6 flex flex-col md:flex-row md:items-center md:justify-between gap-6 print:border-none print:pb-0">
            <div>
              <span className="text-xs font-mono text-muted-foreground uppercase tracking-wider print:hidden">
                Generated Executive Report
              </span>
              <h2 className="font-display text-2xl lg:text-3xl font-bold text-foreground mt-1">
                Analytics Report #{run.id}
              </h2>
              <p className="text-sm text-muted-foreground mt-1 font-sans">
                Generated on {generatedAt} &bull; Run ID {run.id}
              </p>
            </div>
            <div className="flex items-center gap-3 shrink-0 print:hidden">
              <Button
                variant="outline"
                className="font-medium h-10 border-border hover:bg-muted"
                onClick={handlePrint}
              >
                <Printer className="w-4 h-4 mr-2" />
                Print Report
              </Button>
              <Button
                className="font-medium h-10 bg-primary hover:bg-primary/95 text-primary-foreground shadow-sm"
                disabled={!hasPdf}
                onClick={handleDownloadPdf}
              >
                <Download className="w-4 h-4 mr-2" />
                Download PDF
              </Button>
            </div>
          </section>

          {/* Quick Metrics */}
          <section className="print:grid print:grid-cols-5 print:gap-4 print:my-4">
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
              <div className="bg-card border border-border p-4 rounded-xl space-y-1">
                <span className="text-xs font-mono text-muted-foreground uppercase">Dataset Status</span>
                <p className="text-lg font-display font-semibold text-foreground capitalize">{run.status}</p>
              </div>
              <div className="bg-card border border-border p-4 rounded-xl space-y-1">
                <span className="text-xs font-mono text-muted-foreground uppercase">Total Findings</span>
                <p className="text-lg font-display font-semibold text-foreground">{insightCount} insights</p>
              </div>
              <MetricCard
                label="Total Transactions"
                value={
                  run.insight_report?.total_transactions != null
                    ? run.insight_report.total_transactions.toLocaleString()
                    : "—"
                }
              />
              <MetricCard
                label="Products Analyzed"
                value={
                  run.insight_report?.products_analyzed != null
                    ? run.insight_report.products_analyzed.toLocaleString()
                    : run.insight_report?.business_insights?.enhanced_products_to_watch?.total_products_analyzed != null
                    ? run.insight_report.business_insights.enhanced_products_to_watch.total_products_analyzed.toLocaleString()
                    : "—"
                }
              />
              <div className="bg-card border border-border p-4 rounded-xl space-y-1">
                <span className="text-xs font-mono text-muted-foreground uppercase">Baseline</span>
                <p className="text-lg font-display font-semibold text-foreground">
                  {run.baseline_file_path ? "Active" : "None"}
                </p>
              </div>
            </div>
          </section>

          {/* Radial Composite Scores Section */}
          {(rsi || ihs) && (
            <section className="space-y-4 print:break-inside-avoid">
              <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
                Composite Scorecards
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* RSI card */}
                {rsi && (
                  <div className="bg-card border border-border/80 rounded-xl p-6 space-y-4 hover:shadow-md transition-all duration-200">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Activity className="w-4 h-4 text-primary" />
                        <h4 className="font-display font-bold text-foreground text-sm">Revenue Stability Index</h4>
                      </div>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold font-mono uppercase bg-primary/10 text-primary border border-primary/20">
                        {rsi.label}
                      </span>
                    </div>

                    <div className="flex items-center gap-4">
                      <div className="w-16 h-16 rounded-full border-4 border-primary/20 border-t-primary flex items-center justify-center font-display font-bold text-xl text-primary shrink-0">
                        {Math.round(rsi.score)}
                      </div>
                      <div className="space-y-1 min-w-0">
                        <p className="text-xs text-muted-foreground leading-relaxed">
                          {rsi.explanation}
                        </p>
                      </div>
                    </div>

                    {rsi.contributing_factors && rsi.contributing_factors.length > 0 && (
                      <div className="space-y-1.5">
                        <span className="text-[10px] font-mono text-muted-foreground uppercase">Key Factors:</span>
                        <div className="flex flex-wrap gap-1">
                          {rsi.contributing_factors.map((f, i) => (
                            <span key={i} className="text-[10px] px-2 py-0.5 bg-muted rounded border border-border/50 text-foreground font-mono">
                              {f}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {rsi.warning && (
                      <div className="p-2.5 bg-gold/5 border border-gold/25 text-[11px] text-yellow-700 dark:text-gold rounded flex items-start gap-2">
                        <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                        <p>{rsi.warning}</p>
                      </div>
                    )}
                  </div>
                )}

                {/* IHS card */}
                {ihs && (
                  <div className="bg-card border border-border/80 rounded-xl p-6 space-y-4 hover:shadow-md transition-all duration-200">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Award className="w-4 h-4 text-emerald-500" />
                        <h4 className="font-display font-bold text-foreground text-sm">Inventory Health Score</h4>
                      </div>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold font-mono uppercase bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                        {ihs.label}
                      </span>
                    </div>

                    <div className="flex items-center gap-4">
                      <div className="w-16 h-16 rounded-full border-4 border-emerald-500/20 border-t-emerald-500 flex items-center justify-center font-display font-bold text-xl text-emerald-500 shrink-0">
                        {Math.round(ihs.score)}
                      </div>
                      <div className="space-y-1 min-w-0">
                        <p className="text-xs text-muted-foreground leading-relaxed">
                          {ihs.explanation}
                        </p>
                      </div>
                    </div>

                    {ihs.contributing_factors && ihs.contributing_factors.length > 0 && (
                      <div className="space-y-1.5">
                        <span className="text-[10px] font-mono text-muted-foreground uppercase">Inventory Factors:</span>
                        <div className="flex flex-wrap gap-1">
                          {ihs.contributing_factors.map((f, i) => (
                            <span key={i} className="text-[10px] px-2 py-0.5 bg-muted rounded border border-border/50 text-foreground font-mono">
                              {f}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {ihs.warning && (
                      <div className="p-2.5 bg-destructive/5 border border-destructive/20 text-[11px] text-destructive rounded flex items-start gap-2">
                        <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                        <p>{ihs.warning}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </section>
          )}

          {/* Early Warning Alerts Section */}
          {alerts && alerts.alerts && alerts.alerts.length > 0 && (
            <section className="space-y-4 print:break-inside-avoid animate-fade-in">
              <div className="flex items-center gap-2">
                <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
                  Early Warning Alerts
                </h3>
                {alerts.has_critical && (
                  <span className="text-[9px] font-bold font-mono px-1.5 py-0.5 bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20 rounded">
                    CRITICAL
                  </span>
                )}
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {alerts.alerts.map((alert: { severity: string; title: string; description: string; driver?: string; action_direction?: string }, idx: number) => {
                  const severityConfig: Record<string, { border: string; bg: string; text: string }> = {
                    critical: { border: "border-red-500/30", bg: "bg-red-500/5", text: "text-red-600 dark:text-red-400" },
                    high: { border: "border-amber-500/30", bg: "bg-amber-500/5", text: "text-amber-600 dark:text-amber-400" },
                    medium: { border: "border-yellow-500/20", bg: "bg-yellow-500/5", text: "text-yellow-600" },
                    low: { border: "border-border/60", bg: "bg-card", text: "text-muted-foreground" },
                  };
                  const config = severityConfig[alert.severity] || severityConfig.low;

                  return (
                    <div
                      key={idx}
                      className={cn(
                        "border rounded-xl p-5 space-y-3 transition-all duration-200",
                        config.border,
                        config.bg
                      )}
                    >
                      <div className="flex items-center justify-between pb-2 border-b border-border/40">
                        <div className="flex items-center gap-2">
                          <ShieldAlert className={cn("w-4 h-4", config.text)} />
                          <h4 className="font-display font-semibold text-foreground text-sm">
                            {alert.title}
                          </h4>
                        </div>
                        <span className={cn("text-[9px] font-bold font-mono uppercase px-1.5 py-0.5 rounded bg-background border border-border", config.text)}>
                          {alert.severity}
                        </span>
                      </div>
                      
                      <p className="text-xs text-foreground/80 leading-relaxed">
                        {alert.description}
                      </p>

                      {alert.driver && (
                        <div className="text-[11px] leading-normal">
                          <span className="text-muted-foreground font-mono">Driver:</span>{" "}
                          <span className="text-foreground">{alert.driver}</span>
                        </div>
                      )}

                      {alert.action_direction && (
                        <div className="text-[11px] leading-normal">
                          <span className="text-primary font-mono font-semibold">Recommended Action:</span>{" "}
                          <span className="text-foreground">{alert.action_direction}</span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </section>
          )}

          {/* Data Quality Summary */}
          {bi?.data_quality && (
            <section className="space-y-4 print:break-inside-avoid animate-fade-in">
              <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
                Data Quality Summary
              </h3>
              <div className="bg-card border border-border/80 rounded-xl p-6 space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-3">
                    <div className="text-sm">
                      <span className="text-muted-foreground">Cleaning Result:</span>
                      <p className="font-medium text-foreground">
                        {bi.data_quality.rows_after?.toLocaleString()} rows preserved{" "}
                        <span className="text-xs text-muted-foreground font-normal">
                          (from {bi.data_quality.rows_before?.toLocaleString()})
                        </span>
                      </p>
                    </div>
                    {bi.data_quality.granularity && bi.data_quality.granularity.granularity !== "unknown" && (
                      <div className="text-sm">
                        <span className="text-muted-foreground">Granularity:</span>
                        <p className="font-medium text-foreground capitalize">
                          {bi.data_quality.granularity.granularity.replace(/_/g, " ")}
                          <span className="ml-2 text-[10px] font-mono text-muted-foreground">
                            ({bi.data_quality.granularity.confidence?.toUpperCase()} CONFIDENCE)
                          </span>
                        </p>
                        {bi.data_quality.granularity.explanation && (
                          <p className="text-[10px] text-muted-foreground mt-0.5">{bi.data_quality.granularity.explanation}</p>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="space-y-3">
                    {bi.data_quality.schema_detected && bi.data_quality.schema_detected.detected_columns && (
                      <div className="text-sm">
                        <span className="text-muted-foreground">Detected Schema:</span>
                        <div className="flex flex-wrap gap-1.5 mt-1.5">
                          {Object.keys(bi.data_quality.schema_detected.detected_columns).sort().map((field) => (
                            <span key={field} className="px-1.5 py-0.5 bg-muted/50 border border-border/50 text-[10px] font-mono rounded text-muted-foreground">
                              {field}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {bi.data_quality.date_columns_parsed && bi.data_quality.date_columns_parsed.length > 0 && (
                      <div className="text-sm">
                        <span className="text-muted-foreground">Time Series Based On:</span>
                        <p className="font-medium text-foreground mt-0.5 text-xs">
                          Parsed from: <span className="font-mono">{bi.data_quality.date_columns_parsed.join(", ")}</span>
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* Full Insights List */}
          {run.insight_report?.insights && run.insight_report.insights.length > 0 && (
            <section className="space-y-4 print:break-inside-avoid">
              <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
                Automated Insights List
              </h3>
              <div className="space-y-4">
                {run.insight_report.insights.map((insight: { title: string; description: string; driver?: string; implication?: string; action_direction?: string; confidence?: string; confidence_basis?: string; severity?: string }, idx: number) => (
                  <InsightCard
                    key={idx}
                    title={insight.title}
                    description={insight.description}
                    driver={insight.driver}
                    implication={insight.implication}
                    actionDirection={insight.action_direction}
                    confidence={insight.confidence}
                    confidenceBasis={insight.confidence_basis}
                    severity={(insight.severity as InsightSeverity) || "low"}
                    expandable={true}
                    defaultExpanded={insight.severity === "high"}
                    className="print:break-inside-avoid"
                  />
                ))}
              </div>
            </section>
          )}

          {/* Executive Summary Narrative */}
          {bi?.executive_summary && (
            <section className="space-y-4 print:break-inside-avoid">
              <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
                Executive Overview Summary
              </h3>
              <div className="bg-card border border-border/80 rounded-xl p-6 lg:p-8 space-y-4 relative overflow-hidden">
                <div className="absolute top-0 right-0 w-24 h-24 bg-primary/5 rounded-full blur-3xl" />
                <p className="text-foreground leading-relaxed text-sm font-sans relative z-1">
                  {bi.executive_summary}
                </p>
              </div>
            </section>
          )}

          {/* checklist of key takeaways */}
          {bi?.executive_takeaways && bi.executive_takeaways.length > 0 && (
            <section className="space-y-4 print:break-inside-avoid">
              <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
                Strategic Key Takeaways
              </h3>
              <div className="bg-card border border-border/80 rounded-xl p-6">
                <ul className="space-y-3 pl-1">
                  {bi.executive_takeaways.slice(0, 8).map((t: string, idx: number) => (
                    <li key={idx} className="text-sm text-foreground flex items-start gap-3">
                      <span className="w-5 h-5 rounded-full bg-primary/10 border border-primary/20 text-primary flex items-center justify-center font-mono font-bold text-xs shrink-0 mt-0.5">
                        {idx + 1}
                      </span>
                      <p className="leading-relaxed">{t}</p>
                    </li>
                  ))}
                </ul>
              </div>
            </section>
          )}

          {/* PDF Preview Frame Block */}
          {hasPdf ? (
            <section className="space-y-4 print:hidden">
              <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
                Document PDF Artifact
              </h3>
              <div className="bg-card border border-border/80 rounded-xl overflow-hidden shadow-inner">
                <div className="bg-muted/30 border-b border-border px-6 py-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <FileText className="w-4 h-4 text-muted-foreground" />
                    <span className="text-xs text-muted-foreground font-mono">analysis_report_{run.id}.pdf</span>
                  </div>
                  <span className="px-2 py-0.5 rounded text-[9px] font-mono font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                    PDF GEN SUCCESS
                  </span>
                </div>
                <div className="p-10 lg:p-14 bg-background min-h-[300px] flex items-center justify-center">
                  <div className="text-center max-w-sm">
                    <FileText className="w-12 h-12 text-primary/30 mx-auto mb-4" />
                    <h4 className="font-display font-semibold text-foreground text-sm mb-1">
                      Full-Print PDF Report Ready
                    </h4>
                    <p className="text-xs text-muted-foreground mb-6 font-sans">
                      The PDF document has been compiled including high-res visualizations, complete dataset tables, and structured analytical sections.
                    </p>
                    <div className="flex justify-center gap-3">
                      <Button variant="outline" size="sm" onClick={handleDownloadPdf}>
                        Download PDF File
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          ) : (
            <section className="print:hidden">
              <div className="bg-muted/20 border border-border/80 rounded-xl p-10 text-center">
                <FileText className="w-12 h-12 text-muted-foreground/30 mx-auto mb-3" />
                <h4 className="font-semibold text-foreground text-sm mb-1">PDF Offline</h4>
                <p className="text-xs text-muted-foreground max-w-xs mx-auto">
                  Automatic PDF report compilation is disabled or offline. View inline scoring and alerts details above.
                </p>
              </div>
            </section>
          )}

          {/* Footer Metadata */}
          <section className="pt-6 border-t border-border/80 print:break-inside-avoid print:mt-10">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 text-xs text-muted-foreground/75 font-sans">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 shrink-0" />
                <span>Generated {generatedAt}</span>
              </div>
              <div className="flex items-center gap-2 font-mono">
                <Database className="w-4 h-4 shrink-0" />
                <span>WORKSPACE ID: Kaizen_V1 / PIPELINE RUN #{run.id}</span>
              </div>
            </div>
          </section>
        </div>
      </div>
    </AppLayout>
  );
}
