import { AppLayout } from "@/components/layout/AppLayout";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Database, LayoutDashboard } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useLatestCompletedRun } from "@/hooks/useAnalysis";

export default function Overview() {
  const navigate = useNavigate();
  const { data: run, isLoading, error } = useLatestCompletedRun();

  if (isLoading) {
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

  if (error) {
    return (
      <AppLayout>
        <EmptyState
          icon={LayoutDashboard}
          title="Unable to load overview"
          description={error.message || "An error occurred while loading the analysis overview."}
          action={<Button variant="outline" onClick={() => window.location.reload()}>Try again</Button>}
          className="h-[calc(100vh-3.5rem)]"
        />
      </AppLayout>
    );
  }

  if (!run || !run.insight_report) {
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

  const report = run.insight_report;
  const bi = report?.business_insights || null;
  const hasBI =
    !!bi &&
    !!(
      bi.executive_takeaways ||
      bi.executive_summary ||
      bi.trend ||
      bi.stability ||
      bi.efficiency ||
      bi.concentration
    );

  return (
    <AppLayout>
      <div className="page-container animate-fade-in">
        <section className="section-spacing">
          <div className="flex items-center justify-between">
            <p className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
              Data Mode
            </p>
            <StatusBadge
              status={hasBI ? "complete" : "idle"}
              label={hasBI ? "Business Insights Active" : "Legacy Fields"}
            />
          </div>
        </section>
        {bi?.executive_takeaways && Array.isArray(bi.executive_takeaways) && bi.executive_takeaways.length > 0 && (
          <section className="section-spacing">
            <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider mb-4">Executive Takeaways</h3>
            <div className="bg-card border border-border rounded-lg p-6">
              <ul className="list-disc pl-5 space-y-2">
                {bi.executive_takeaways.slice(0, 6).map((t, idx) => (
                  <li key={idx} className="text-sm text-foreground">{t}</li>
                ))}
              </ul>
            </div>
          </section>
        )}

        <section className="section-spacing">
          <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider mb-4">Executive Summary</h3>
          <div className="bg-card border border-border rounded-lg p-8">
            <p className="text-foreground leading-reading text-base">
              {report.summary || report.executive_summary || "No summary available."}
            </p>
          </div>
        </section>

        <section className="section-spacing">
          <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider mb-4">Signals</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-card border border-border rounded-lg p-5 space-y-2">
              <p className="text-xs text-muted-foreground">Trend Direction</p>
              <StatusBadge status="complete" label={bi?.trend?.direction || report.trend_direction || "—"} />
            </div>
            <div className="bg-card border border-border rounded-lg p-5 space-y-2">
              <p className="text-xs text-muted-foreground">Stability</p>
              <StatusBadge status="complete" label={bi?.stability?.category || report.stability || "—"} />
            </div>
            <div className="bg-card border border-border rounded-lg p-5 space-y-2">
              <p className="text-xs text-muted-foreground">Efficiency Signal</p>
              <StatusBadge status="complete" label={bi?.efficiency?.signal || report.efficiency_signal || "—"} />
            </div>
            <div className="bg-card border border-border rounded-lg p-5 space-y-2">
              <p className="text-xs text-muted-foreground">Concentration Risk</p>
              <StatusBadge status="complete" label={bi?.concentration?.risk_level || report.concentration_risk || "—"} />
            </div>
          </div>
        </section>
      </div>
    </AppLayout>
  );
}
