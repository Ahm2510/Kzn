import { AppLayout } from "@/components/layout/AppLayout";
import { InsightCard, InsightSeverity } from "@/components/ui/InsightCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Lightbulb, Database } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useLatestCompletedRun } from "@/hooks/useAnalysis";

export default function Insights() {
  const navigate = useNavigate();
  const { data: run, isLoading, error } = useLatestCompletedRun();

  if (isLoading) {
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

  if (error) {
    return (
      <AppLayout>
        <EmptyState
          icon={Lightbulb}
          title="Unable to load insights"
          description={error.message || "An error occurred while loading insights."}
          action={<Button variant="outline" onClick={() => window.location.reload()}>Try again</Button>}
          className="h-[calc(100vh-3.5rem)]"
        />
      </AppLayout>
    );
  }

  const insights = run?.insight_report?.insights;

  if (!insights || insights.length === 0) {
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

  return (
    <AppLayout>
      <div className="page-container animate-fade-in">
        <section className="section-spacing">
          <p className="text-sm text-muted-foreground font-mono mb-6">
            {insights.length} insight{insights.length !== 1 ? "s" : ""} generated
          </p>
          <div className="space-y-4">
            {insights.map((insight) => (
              <InsightCard
                key={insight.id}
                title={insight.title}
                description={insight.description}
                driver={insight.driver}
                implication={insight.implication}
                actionDirection={insight.action_direction}
                confidence={insight.confidence}
                confidenceBasis={insight.confidence_basis}
                severity={insight.severity as InsightSeverity}
              />
            ))}
          </div>
        </section>
      </div>
    </AppLayout>
  );
}
