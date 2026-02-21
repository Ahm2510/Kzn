import { useEffect, useMemo, useState } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { MetricCard } from "@/components/ui/MetricCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { GitCompare, Database } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

import * as serviceA from "@/api/serviceA";

// Checklist §8: Only ONE metric — current, baseline, absolute change, percent change
interface ComparisonData {
  metricName: string;
  currentValue: string;
  baselineValue: string;
  absoluteChange: string;
  percentChange: string;
}

type ComparisonState =
  | { status: "loading" }
  | { status: "empty" }
  | { status: "error"; message: string }
  | { status: "success"; data: ComparisonData };

export default function Comparison() {
  const navigate = useNavigate();
  const location = useLocation();

  const runId = useMemo(() => {
    const q = new URLSearchParams(location.search);
    const raw = q.get("id");
    if (!raw) return null;
    const n = Number(raw);
    return Number.isFinite(n) ? n : null;
  }, [location.search]);

  const [state, setState] = useState<ComparisonState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;

    const pickDelta = (report: any): any | null => {
      if (!report) return null;
      if (report.metric_delta) return report.metric_delta;
      if (Array.isArray(report.metric_deltas) && report.metric_deltas.length > 0) return report.metric_deltas[0];
      if (Array.isArray(report.deltas) && report.deltas.length > 0) return report.deltas[0];
      return null;
    };

    (async () => {
      if (!runId) {
        setState({ status: "empty" });
        return;
      }

      setState({ status: "loading" });
      try {
        const run = await serviceA.getAnalysisRun(runId);
        if (cancelled) return;

        if (!run.baseline_file_path) {
          setState({ status: "empty" });
          return;
        }

        const report = run.insight_report as any;
        const delta = pickDelta(report);
        if (!delta) {
          setState({ status: "error", message: "No comparison metric available." });
          return;
        }

        const metricName = String(delta.metric ?? delta.metric_name ?? delta.name ?? "Metric");
        const currentValue = String(delta.current_value ?? delta.current ?? "");
        const baselineValue = String(delta.baseline_value ?? delta.baseline ?? "");
        const absoluteChange = String(delta.absolute_change ?? delta.absolute ?? delta.delta ?? "");
        const percentChange = String(delta.percent_change ?? delta.percent ?? "");

        setState({
          status: "success",
          data: {
            metricName,
            currentValue,
            baselineValue,
            absoluteChange,
            percentChange,
          },
        });
      } catch (e) {
        if (cancelled) return;
        const err = e as { status?: number };
        if (err?.status === 403) {
          setState({ status: "error", message: "Not authenticated. Please login again." });
        } else {
          setState({ status: "error", message: "Unable to load comparison data." });
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [runId]);

  // Loading state
  if (state.status === "loading") {
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

  // Error state
  if (state.status === "error") {
    return (
      <AppLayout>
        <EmptyState
          icon={GitCompare}
          title="Unable to load comparison"
          description={state.message || "An error occurred while loading comparison data."}
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

  // Empty state — no baseline dataset provided
  if (state.status === "empty") {
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

  // Success state — single metric comparison
  const { data } = state;

  return (
    <AppLayout>
      <div className="page-container animate-fade-in">
        {/* Metric label */}
        <section className="section-spacing">
          <div className="bg-card border border-border rounded-lg p-5 space-y-1">
            <p className="text-xs text-muted-foreground uppercase tracking-wider">Comparing Metric</p>
            <p className="text-base font-semibold text-foreground">{data.metricName}</p>
          </div>
        </section>

        {/* Four cards: Current, Baseline, Absolute Change, % Change */}
        <section className="section-spacing">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard label="Current" value={data.currentValue} />
            <MetricCard label="Baseline" value={data.baselineValue} />
            <MetricCard label="Absolute Change" value={data.absoluteChange} />
            <MetricCard label="% Change" value={data.percentChange} />
          </div>
        </section>
      </div>
    </AppLayout>
  );
}
