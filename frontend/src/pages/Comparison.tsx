import { AppLayout } from "@/components/layout/AppLayout";
import { MetricCard } from "@/components/ui/MetricCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { GitCompare, Database } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useLatestCompletedRun } from "@/hooks/useAnalysis";

export default function Comparison() {
  const navigate = useNavigate();
  const { data: run, isLoading, error } = useLatestCompletedRun();

  if (isLoading) {
    return (
      <AppLayout>
        <div className="page-container animate-fade-in">
          <section className="section-spacing">
            <Skeleton className="h-6 w-48 mb-6" />
            <Skeleton className="h-20 w-full rounded-lg mb-4" />
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Skeleton className="h-24 rounded-lg" />
              <Skeleton className="h-24 rounded-lg" />
              <Skeleton className="h-24 rounded-lg" />
              <Skeleton className="h-24 rounded-lg" />
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
          icon={GitCompare}
          title="Unable to load comparison"
          description={error.message || "An error occurred while loading comparison data."}
          action={<Button variant="outline" onClick={() => window.location.reload()}>Try again</Button>}
          className="h-[calc(100vh-3.5rem)]"
        />
      </AppLayout>
    );
  }

  const comparison = run?.insight_report?.comparison;

  if (!comparison) {
    return (
      <AppLayout>
        <EmptyState
          icon={GitCompare}
          title="No comparison dataset provided"
          description="Upload a baseline dataset alongside your primary dataset to enable period-over-period comparison."
          action={
            <Button onClick={() => navigate("/datasets")}>
              <Database className="w-4 h-4 mr-2" />
              Upload datasets
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
        <section className="section-spacing">
          <div className="bg-card border border-border rounded-lg p-5 space-y-1">
            <p className="text-xs text-muted-foreground uppercase tracking-wider">Comparing Metric</p>
            <p className="text-base font-semibold text-foreground">{comparison.metric_name}</p>
          </div>
        </section>
        <section className="section-spacing">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard label="Current" value={comparison.current_value} />
            <MetricCard label="Baseline" value={comparison.baseline_value} />
            <MetricCard label="Absolute Change" value={comparison.absolute_change} />
            <MetricCard label="% Change" value={comparison.percent_change} />
          </div>
        </section>
      </div>
    </AppLayout>
  );
}
