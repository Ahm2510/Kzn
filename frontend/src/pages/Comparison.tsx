import { AppLayout } from "@/components/layout/AppLayout";
import { MetricCard } from "@/components/ui/MetricCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { GitCompare, Database, ArrowUpRight, ArrowDownRight, RefreshCw, AlertTriangle, TrendingUp, Info } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useLatestCompletedRun } from "@/hooks/useAnalysis";
import { cn } from "@/lib/utils";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";

export default function Comparison() {
  const navigate = useNavigate();
  const { data: run, isLoading, error } = useLatestCompletedRun();

  if (isLoading) {
    return (
      <AppLayout>
        <div className="page-container animate-fade-in">
          <section className="section-spacing">
            <Skeleton className="h-6 w-48 mb-6" />
            <Skeleton className="h-28 w-full rounded-xl mb-6" />
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              <Skeleton className="h-24 rounded-lg" />
              <Skeleton className="h-24 rounded-lg" />
              <Skeleton className="h-24 rounded-lg" />
              <Skeleton className="h-24 rounded-lg" />
            </div>
            <Skeleton className="h-80 w-full rounded-xl" />
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
  const bi = run?.insight_report?.business_insights;
  const mom = bi?.mom_commentary;

  if (!comparison) {
    return (
      <AppLayout>
        <EmptyState
          icon={GitCompare}
          title="No comparison dataset provided"
          description="Upload a baseline dataset alongside your primary dataset to enable deep period-over-period performance comparisons."
          action={
            <Button onClick={() => navigate("/datasets")} className="bg-primary hover:bg-primary/95 text-primary-foreground">
              <Database className="w-4 h-4 mr-2" />
              Upload datasets
            </Button>
          }
          className="h-[calc(100vh-3.5rem)]"
        />
      </AppLayout>
    );
  }

  // Parse values to numeric format for charts
  const parseNumber = (val: string | number | null | undefined): number => {
    if (val == null) return 0;
    if (typeof val === "number") return val;
    const parsed = parseFloat(val.replace(/[^0-9.-]/g, ""));
    return isNaN(parsed) ? 0 : parsed;
  };

  const currentValNum = parseNumber(comparison.current_value);
  const baselineValNum = parseNumber(comparison.baseline_value);
  const percentChangeNum = parseNumber(comparison.percent_change);

  // Determine direction
  const direction = mom?.direction
    ? mom.direction
    : percentChangeNum > 0
    ? "positive"
    : percentChangeNum < 0
    ? "negative"
    : "flat";

  // Recharts Chart Data
  const chartData = [
    {
      name: comparison.metric_name || "Metric",
      Baseline: baselineValNum,
      Current: currentValNum,
    },
  ];

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    }).format(val);
  };

  return (
    <AppLayout>
      <div className="page-container animate-fade-in">
        {/* Header Title Block */}
        <section className="mb-6">
          <p className="text-sm font-mono text-muted-foreground uppercase tracking-wider">
            Comparative Analytics
          </p>
          <h2 className="text-3xl font-display font-bold text-foreground mt-1">
            Period-over-Period Comparison
          </h2>
        </section>

        {/* Direction Banner */}
        <section className="section-spacing">
          <div
            className={cn(
              "border rounded-xl p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 transition-all duration-300",
              direction === "positive" && "bg-emerald-500/5 border-emerald-500/20 text-emerald-800 dark:text-emerald-300 shadow-sm shadow-emerald-500/5",
              direction === "negative" && "bg-destructive/5 border-destructive/20 text-destructive dark:text-red-400 shadow-sm shadow-destructive/5",
              direction === "flat" && "bg-muted/30 border-border text-muted-foreground"
            )}
          >
            <div className="flex items-start gap-4">
              <div
                className={cn(
                  "p-3 rounded-xl shrink-0 mt-0.5",
                  direction === "positive" && "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
                  direction === "negative" && "bg-destructive/10 text-destructive dark:text-red-400",
                  direction === "flat" && "bg-muted text-muted-foreground"
                )}
              >
                {direction === "positive" ? (
                  <ArrowUpRight className="w-6 h-6 animate-pulse" />
                ) : direction === "negative" ? (
                  <ArrowDownRight className="w-6 h-6 animate-pulse" />
                ) : (
                  <RefreshCw className="w-6 h-6" />
                )}
              </div>
              <div className="space-y-1">
                <h3 className="text-lg font-display font-bold text-foreground">
                  {direction === "positive"
                    ? "Growth Performance Detected"
                    : direction === "negative"
                    ? "Performance Decline Detected"
                    : "Stable/Flat Growth Performance"}
                </h3>
                <p className="text-sm text-muted-foreground leading-relaxed max-w-2xl font-sans">
                  Comparing current dataset periods to the baseline. 
                  {direction === "positive" && ` Outstanding gains of ${comparison.percent_change} were calculated across core revenue streams.`}
                  {direction === "negative" && ` A drop of ${comparison.percent_change} was detected. Immediate actions and drivers are detailed below.`}
                  {direction === "flat" && " Stable performance relative to the baseline period with no significant volatility."}
                </p>
              </div>
            </div>
            
            <div className="shrink-0 text-left md:text-right bg-background/50 border border-border/40 px-4 py-2 rounded-lg font-mono">
              <span className="text-[10px] text-muted-foreground uppercase block font-semibold">Magnitude</span>
              <span className={cn(
                "text-sm font-bold uppercase",
                direction === "positive" && "text-emerald-500",
                direction === "negative" && "text-destructive",
                direction === "flat" && "text-muted-foreground"
              )}>
                {mom?.magnitude || (percentChangeNum > 10 || percentChangeNum < -10 ? "strong" : "moderate")}
              </span>
            </div>
          </div>
        </section>

        {/* Metric Cards Grid */}
        <section className="section-spacing">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard
              label="Current Period Value"
              value={comparison.current_value}
              className="bg-card"
            />
            <MetricCard
              label="Baseline Period Value"
              value={comparison.baseline_value}
              className="bg-card"
            />
            <MetricCard
              label="Absolute Change"
              value={comparison.absolute_change}
              trend={percentChangeNum > 0 ? "up" : percentChangeNum < 0 ? "down" : "flat"}
              className="bg-card"
            />
            <MetricCard
              label="Relative Change"
              value={comparison.percent_change}
              trend={percentChangeNum > 0 ? "up" : percentChangeNum < 0 ? "down" : "flat"}
              className="bg-card font-mono"
            />
          </div>
        </section>

        {/* Side-by-Side Visualization + MoM Commentary Details */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-6 section-spacing">
          {/* Recharts Bar Chart */}
          <div className="lg:col-span-7 bg-card border border-border rounded-xl p-5 md:p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-border/60">
              <div>
                <span className="text-[10px] font-mono text-muted-foreground uppercase font-semibold">Visual comparison</span>
                <h4 className="font-display font-semibold text-foreground text-sm">
                  {comparison.metric_name} Metric Distribution
                </h4>
              </div>
              <TrendingUp className="w-4 h-4 text-primary" />
            </div>

            <div className="h-72 w-full pt-4">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 30, left: 10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.4} />
                  <XAxis dataKey="name" stroke="var(--muted-foreground)" fontSize={11} tickLine={false} />
                  <YAxis
                    stroke="var(--muted-foreground)"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v) => (v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v)}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "var(--card)",
                      borderColor: "var(--border)",
                      color: "var(--foreground)",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                    formatter={(value: number | string) => [formatCurrency(Number(value)), "Value"]}
                  />
                  <Legend verticalAlign="top" height={36} iconType="circle" />
                  <Bar
                    dataKey="Baseline"
                    name="Baseline Period"
                    fill="hsl(var(--muted-foreground))"
                    radius={[4, 4, 0, 0]}
                    opacity={0.75}
                  />
                  <Bar
                    dataKey="Current"
                    name="Current Period"
                    fill="hsl(var(--primary))"
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Deep Narrative Commentary */}
          <div className="lg:col-span-5 flex flex-col justify-between bg-card border border-border rounded-xl p-5 md:p-6 space-y-4">
            <div className="space-y-4">
              <div className="flex items-center gap-2 pb-3 border-b border-border/60">
                <Info className="w-4 h-4 text-primary" />
                <h4 className="font-display font-semibold text-foreground text-sm">
                  Period Narrative & Insights
                </h4>
              </div>

              {mom?.commentary ? (
                <div className="space-y-4">
                  <div className="p-4 bg-muted/30 border border-border/40 rounded-lg italic text-sm text-foreground leading-relaxed">
                    "{mom.commentary}"
                  </div>

                  {mom.interpretation && (
                    <div className="text-xs space-y-1">
                      <span className="text-muted-foreground uppercase font-mono tracking-wider block">Interpretation:</span>
                      <p className="text-foreground leading-relaxed">{mom.interpretation}</p>
                    </div>
                  )}

                  {mom.driver_hint && (
                    <div className="text-xs p-3 rounded-lg border border-primary/10 bg-primary/5 flex gap-2">
                      <span className="font-mono text-primary font-bold">DRIVER:</span>
                      <p className="text-foreground">{mom.driver_hint}</p>
                    </div>
                  )}

                  {mom.confidence && (
                    <div className="flex items-center gap-2 text-xs font-mono">
                      <span className="text-muted-foreground">Confidence Basis:</span>
                      <span className="px-1.5 py-0.5 rounded bg-primary/10 text-primary uppercase font-bold text-[10px]">
                        {mom.confidence}
                      </span>
                      {mom.sample_size && (
                        <span className="text-muted-foreground/60">(n={mom.sample_size})</span>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <div className="space-y-3 text-xs leading-relaxed text-muted-foreground font-sans">
                  <p>
                    No detailed narrative summary was generated by the backend view pipeline.
                  </p>
                  <p>
                    Based on statistical fluctuations, your key metrics shifted by <strong className="text-foreground">{comparison.percent_change}</strong>. This constitutes a <strong className="text-foreground">{direction}</strong> adjustment relative to baseline period limits.
                  </p>
                  <p>
                    Ensure outlier filters and duplicates drop models were properly applied in Datasets settings to get finer narrative correlations in subsequent runs.
                  </p>
                </div>
              )}
            </div>

            {mom?.warning && (
              <div className="mt-4 p-3 bg-destructive/5 border border-destructive/15 text-destructive rounded-lg flex items-start gap-2.5 text-xs animate-pulse-slow">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold block mb-0.5">Statistical Warning:</span>
                  <p>{mom.warning}</p>
                </div>
              </div>
            )}
          </div>
        </section>
      </div>
    </AppLayout>
  );
}
