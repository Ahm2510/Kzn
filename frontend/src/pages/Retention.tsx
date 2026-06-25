import { AppLayout } from "@/components/layout/AppLayout";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { RefreshCw, ArrowUpRight, ArrowDownRight, AlertTriangle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useLatestCompletedRun } from "@/hooks/useAnalysis";

export default function Retention() {
  const navigate = useNavigate();
  const { data: run, isLoading, error } = useLatestCompletedRun();

  if (isLoading) {
    return (
      <AppLayout>
        <div className="page-container animate-fade-in">
          <section className="section-spacing">
            <Skeleton className="h-6 w-48 mb-6" />
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
              <Skeleton className="h-24 rounded-lg" />
              <Skeleton className="h-24 rounded-lg" />
              <Skeleton className="h-24 rounded-lg" />
              <Skeleton className="h-24 rounded-lg" />
            </div>
            <Skeleton className="h-32 w-full rounded-lg mb-8" />
            <Skeleton className="h-96 w-full rounded-lg" />
          </section>
        </div>
      </AppLayout>
    );
  }

  if (error) {
    return (
      <AppLayout>
        <EmptyState
          icon={RefreshCw}
          title="Unable to load retention analysis"
          description={error.message || "An error occurred while loading retention data."}
          action={<Button variant="outline" onClick={() => window.location.reload()}>Try again</Button>}
          className="h-[calc(100vh-3.5rem)]"
        />
      </AppLayout>
    );
  }

  const retentionData = run?.insight_report?.business_insights?.cohort_retention;

  if (!retentionData) {
    return (
      <AppLayout>
        <EmptyState
          icon={RefreshCw}
          title="No customer retention data available"
          description="This analysis requires both a customer ID column (e.g. customer_id) and a date column (e.g. order_date) in your dataset."
          action={
            <Button onClick={() => navigate("/datasets")}>
              Upload new dataset
            </Button>
          }
          className="h-[calc(100vh-3.5rem)]"
        />
      </AppLayout>
    );
  }

  const { summary, cohort_table } = retentionData;

  const getCellColor = (pct: number) => {
    if (pct === 100) return "bg-emerald-500/20 text-emerald-500";
    if (pct >= 60) return "bg-emerald-500/15 text-emerald-400";
    if (pct >= 40) return "bg-amber-500/15 text-amber-400";
    if (pct >= 20) return "bg-amber-500/10 text-amber-500";
    if (pct > 0) return "bg-red-500/10 text-red-400";
    return "bg-muted/20 text-muted-foreground";
  };

  const allPeriodLabels = Array.from(
    new Set(cohort_table.flatMap((row) => row.period_labels))
  ).sort((a, b) => {
    const aNum = parseInt(a.replace(/[^0-9]/g, "")) || 0;
    const bNum = parseInt(b.replace(/[^0-9]/g, "")) || 0;
    return aNum - bNum;
  });

  return (
    <AppLayout>
      <div className="page-container animate-fade-in">
        <section className="section-spacing">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-display font-semibold text-foreground tracking-tight">
              Customer Retention
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="bg-card border border-border rounded-lg p-5 flex flex-col justify-between">
              <p className="text-xs text-muted-foreground mb-2">Repeat Purchase Rate</p>
              <div className={`text-3xl font-display font-bold ${
                summary.repeat_purchase_rate >= 40 ? "text-emerald-500" :
                summary.repeat_purchase_rate >= 20 ? "text-amber-500" :
                "text-red-500"
              }`}>
                {typeof summary.repeat_purchase_rate === 'number' ? summary.repeat_purchase_rate.toFixed(1) : "—"}%
              </div>
            </div>

            <div className="bg-card border border-border rounded-lg p-5 flex flex-col justify-between">
              <p className="text-xs text-muted-foreground mb-2">Avg Orders / Customer</p>
              <div className="text-3xl font-display font-bold text-foreground">
                {typeof summary.avg_orders_per_customer === 'number' ? summary.avg_orders_per_customer.toFixed(1) : "—"}
              </div>
            </div>

            <div className="bg-card border border-border rounded-lg p-5 flex flex-col justify-between">
              <p className="text-xs text-muted-foreground mb-2">Single-Purchase Customers</p>
              <div className={`text-3xl font-display font-bold ${
                summary.single_purchase_customers_pct <= 50 ? "text-emerald-500" :
                summary.single_purchase_customers_pct <= 75 ? "text-amber-500" :
                "text-red-500"
              }`}>
                {typeof summary.single_purchase_customers_pct === 'number' ? summary.single_purchase_customers_pct.toFixed(1) : "—"}%
              </div>
            </div>

            <div className="bg-card border border-border rounded-lg p-5 flex flex-col justify-between">
              <p className="text-xs text-muted-foreground mb-2">Cohort Trend</p>
              <div className="flex items-center gap-2">
                <div className={`text-2xl font-display font-bold capitalize ${
                  summary.cohort_trend === "improving" ? "text-emerald-500" :
                  summary.cohort_trend === "declining" ? "text-red-500" :
                  "text-foreground"
                }`}>
                  {summary.cohort_trend}
                </div>
                {summary.cohort_trend === "improving" && <ArrowUpRight className="w-6 h-6 text-emerald-500" />}
                {summary.cohort_trend === "declining" && <ArrowDownRight className="w-6 h-6 text-red-500" />}
              </div>
            </div>
          </div>

          {summary.cohort_trend === "declining" && (
            <div className="mb-6 p-4 bg-amber-500/5 border border-amber-500/40 rounded-lg flex gap-3 items-start">
              <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
              <p className="text-sm text-foreground/90">
                Retention is declining — recent customer cohorts are returning at lower rates than earlier cohorts.
              </p>
            </div>
          )}

          {summary.at_risk_cohorts && Array.isArray(summary.at_risk_cohorts) && summary.at_risk_cohorts.length > 0 && (
            <div className="mb-6 p-4 bg-red-500/5 border border-red-500/40 rounded-lg flex gap-3 items-start animate-pulse">
              <AlertTriangle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-semibold text-red-500 mb-1">
                  At-Risk Cohorts Detected
                </p>
                <p className="text-sm text-foreground/90">
                  The following cohorts had less than 20% retention by their second period:{" "}
                  <span className="font-mono">{summary.at_risk_cohorts.join(", ")}</span>
                </p>
              </div>
            </div>
          )}

          <div className="bg-card border border-border rounded-lg overflow-hidden mb-6">
            <div className="p-4 border-b border-border flex justify-between items-center">
              <h3 className="text-sm font-medium text-foreground">Cohort Survival Heatmap</h3>
              <StatusBadge status="complete" label={retentionData.analysis_granularity} />
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm whitespace-nowrap">
                <thead className="bg-muted/50 text-muted-foreground text-xs font-mono uppercase">
                  <tr>
                    <th className="px-4 py-3 font-medium">Cohort</th>
                    <th className="px-4 py-3 font-medium text-right">Size</th>
                    {allPeriodLabels.map((label, i) => (
                      <th key={i} className="px-4 py-3 font-medium text-center">{label}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {cohort_table.map((row, idx) => (
                    <tr key={idx} className="hover:bg-muted/30 transition-colors">
                      <td className="px-4 py-3">
                        <div className="font-medium text-foreground">{row.cohort_label}</div>
                      </td>
                      <td className="px-4 py-3 text-right text-muted-foreground">
                        {row.cohort_size.toLocaleString()}
                      </td>
                      {allPeriodLabels.map((_, i) => {
                        const pct = row.periods[i];
                        if (pct === undefined) {
                          return <td key={i} className="px-4 py-3 text-center text-muted-foreground">—</td>;
                        }
                        const cellColorClass = getCellColor(pct);
                        return (
                          <td key={i} className="px-1 py-1">
                            <div className={`w-full h-full min-h-[2.5rem] rounded-md flex items-center justify-center font-mono text-xs font-medium ${cellColorClass}`}>
                              {pct.toFixed(0)}%
                            </div>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                  {cohort_table.length === 0 && (
                    <tr>
                      <td colSpan={allPeriodLabels.length + 2} className="px-4 py-8 text-center text-muted-foreground">
                        No cohorts available.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="bg-muted/30 border border-border/50 rounded-lg p-5">
            <p className="text-sm text-foreground/90 leading-relaxed mb-4">
              {retentionData.explanation}
            </p>
            {retentionData.warning && (
              <p className="text-xs text-amber-500 font-medium mb-4">
                ⚠ {retentionData.warning}
              </p>
            )}
            <div className="flex items-center justify-between border-t border-border/50 pt-4 mt-2">
              <p className="text-xs text-muted-foreground font-mono">
                Customer ID: <span className="font-bold">{retentionData.customer_column_used}</span> · Date: <span className="font-bold">{retentionData.date_column_used}</span>
              </p>
              <p className="text-[10px] text-muted-foreground font-mono">
                Confidence: {retentionData.confidence?.toUpperCase()} ({retentionData.sample_size?.toLocaleString()} records)
              </p>
            </div>
          </div>

        </section>
      </div>
    </AppLayout>
  );
}
