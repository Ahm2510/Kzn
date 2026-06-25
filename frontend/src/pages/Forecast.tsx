import { AppLayout } from "@/components/layout/AppLayout";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { MetricCard } from "@/components/ui/MetricCard";
import { Button } from "@/components/ui/button";
import {
  ResponsiveContainer, ComposedChart, Line, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ReferenceLine,
} from "recharts";
import { TrendingUp, TrendingDown, Minus, Database, AlertTriangle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useLatestCompletedRun } from "@/hooks/useAnalysis";

export default function Forecast() {
  const navigate = useNavigate();
  const { data: run, isLoading, error } = useLatestCompletedRun();

  if (isLoading) {
    return (
      <AppLayout>
        <div className="page-container animate-fade-in">
          <Skeleton className="h-6 w-48 mb-6" />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <Skeleton className="h-24 rounded-lg" />
            <Skeleton className="h-24 rounded-lg" />
            <Skeleton className="h-24 rounded-lg" />
          </div>
          <Skeleton className="h-80 rounded-lg" />
        </div>
      </AppLayout>
    );
  }

  const forecast = run?.insight_report?.business_insights?.forecast;

  if (!run || !run.insight_report) {
    return (
      <AppLayout>
        <EmptyState
          icon={Database}
          title="No analysis available"
          description="Upload a dataset to generate a revenue forecast."
          action={<Button onClick={() => navigate("/datasets")}>Upload Dataset</Button>}
          className="h-[calc(100vh-3.5rem)]"
        />
      </AppLayout>
    );
  }

  if (!forecast) {
    return (
      <AppLayout>
        <div className="page-container animate-fade-in">
          <EmptyState
            icon={TrendingUp}
            title="Forecast unavailable"
            description="This dataset does not have enough historical data points to generate a reliable projection. A minimum of 4 periods is required."
            className="h-[calc(100vh-3.5rem)]"
          />
        </div>
      </AppLayout>
    );
  }

  // Build chart data: combine historical + projected
  const historicalData = forecast.historical_points.map((p) => ({
    label: p.period_label,
    actual: p.projected_value,
    projected: null as number | null,
    lower: null as number | null,
    upper: null as number | null,
    type: "historical" as const,
  }));

  const projectedData = forecast.projected_points.map((p) => ({
    label: p.period_label,
    actual: null as number | null,
    projected: p.projected_value,
    lower: p.lower_bound,
    upper: p.upper_bound,
    type: "projected" as const,
  }));

  // Bridge point: connect historical line to projected line
  const lastHistorical = forecast.historical_points[forecast.historical_points.length - 1];
  const bridgePoint = {
    label: lastHistorical.period_label,
    actual: lastHistorical.projected_value,
    projected: lastHistorical.projected_value,
    lower: lastHistorical.projected_value,
    upper: lastHistorical.projected_value,
    type: "bridge" as const,
  };

  const chartData = [...historicalData, bridgePoint, ...projectedData];

  const TrendIcon =
    forecast.trend_direction === "upward" ? TrendingUp :
    forecast.trend_direction === "downward" ? TrendingDown : Minus;

  const trendColor =
    forecast.trend_direction === "upward" ? "text-emerald-500" :
    forecast.trend_direction === "downward" ? "text-red-500" :
    "text-muted-foreground";

  const nextPeriod = forecast.projected_points[0];
  const lastActual = forecast.historical_points[forecast.historical_points.length - 1];
  const changeVsLast = lastActual
    ? ((nextPeriod.projected_value - lastActual.projected_value) / Math.abs(lastActual.projected_value || 1)) * 100
    : null;

  const formatRevenue = (v: number) => {
    if (typeof v !== 'number') return "—";
    return v >= 1_000_000 ? `$${(v / 1_000_000).toFixed(1)}M` :
           v >= 1_000 ? `$${(v / 1_000).toFixed(0)}K` : `$${v.toFixed(0)}`;
  };

  return (
    <AppLayout>
      <div className="page-container animate-fade-in">

        {/* Header */}
        <section className="section-spacing-sm">
          <div className="flex items-center justify-between mb-2">
            <h1 className="font-display font-bold text-2xl text-foreground">
              Revenue Forecast
            </h1>
            <span className={`flex items-center gap-1.5 text-xs font-mono px-2 py-1 rounded border ${
              forecast.confidence === "high"
                ? "border-emerald-500/30 text-emerald-500 bg-emerald-500/5"
                : forecast.confidence === "medium"
                ? "border-amber-500/30 text-amber-500 bg-amber-500/5"
                : "border-red-500/30 text-red-500 bg-red-500/5"
            }`}>
              {forecast.confidence.toUpperCase()} CONFIDENCE · R²={forecast.r_squared.toFixed(2)}
            </span>
          </div>
          <p className="text-sm text-muted-foreground">{forecast.explanation}</p>
          {forecast.warning && (
            <div className="flex items-start gap-2 mt-3 bg-amber-500/5 border border-amber-500/20 rounded-lg px-4 py-3">
              <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
              <p className="text-xs text-amber-600 dark:text-amber-400">{forecast.warning}</p>
            </div>
          )}
        </section>

        {/* Summary MetricCards */}
        <section className="section-spacing-sm">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <MetricCard
              label="Next Period Projection"
              value={nextPeriod ? formatRevenue(nextPeriod.projected_value) : "—"}
              delta={changeVsLast != null ? `${changeVsLast >= 0 ? "+" : ""}${changeVsLast.toFixed(1)}% vs last` : undefined}
              deltaType={changeVsLast == null ? "neutral" : changeVsLast >= 0 ? "positive" : "negative"}
            />
            <MetricCard
              label="Trend Direction"
              value={forecast.trend_direction.charAt(0).toUpperCase() + forecast.trend_direction.slice(1)}
              delta={`${forecast.trend_slope >= 0 ? "+" : ""}${formatRevenue(forecast.trend_slope)} / period`}
              deltaType={forecast.trend_direction === "upward" ? "positive" : forecast.trend_direction === "downward" ? "negative" : "neutral"}
            />
            <MetricCard
              label="Confidence Basis"
              value={`${forecast.sample_size} periods`}
              delta={forecast.granularity.replace("_", " ")}
              deltaType="neutral"
            />
          </div>
        </section>

        {/* Chart */}
        <section className="section-spacing">
          <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider mb-4">
            Historical + Projected Revenue
          </h3>
          <div className="bg-card border border-border rounded-lg p-6">
            <ResponsiveContainer width="100%" height={360}>
              <ComposedChart data={chartData} margin={{ top: 10, right: 20, left: 20, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis
                  dataKey="label"
                  tick={{ fontSize: 10, fontFamily: "Roboto Mono", fill: "hsl(var(--muted-foreground))" }}
                  angle={-30}
                  textAnchor="end"
                  height={50}
                />
                <YAxis
                  tick={{ fontSize: 11, fontFamily: "Roboto Mono", fill: "hsl(var(--muted-foreground))" }}
                  tickFormatter={formatRevenue}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "6px",
                    fontSize: 12,
                  }}
                  formatter={(value: number, name: string) => [
                    value != null ? formatRevenue(value) : "—",
                    name === "actual" ? "Actual" :
                    name === "projected" ? "Projected" :
                    name === "lower" ? "Lower bound" : "Upper bound",
                  ]}
                />
                <Legend wrapperStyle={{ fontSize: 12, fontFamily: "Roboto Mono" }} />

                {/* Confidence band (area between lower and upper) */}
                <Area
                  type="monotone"
                  dataKey="upper"
                  stroke="none"
                  fill="hsl(var(--primary))"
                  fillOpacity={0.08}
                  name="Upper bound"
                  legendType="none"
                  connectNulls
                />
                <Area
                  type="monotone"
                  dataKey="lower"
                  stroke="none"
                  fill="hsl(var(--background))"
                  fillOpacity={1}
                  name="Lower bound"
                  legendType="none"
                  connectNulls
                />

                {/* Historical line */}
                <Line
                  type="monotone"
                  dataKey="actual"
                  stroke="hsl(var(--primary))"
                  strokeWidth={2}
                  dot={{ r: 3, fill: "hsl(var(--primary))" }}
                  name="Actual"
                  connectNulls={false}
                />

                {/* Projected line (dashed) */}
                <Line
                  type="monotone"
                  dataKey="projected"
                  stroke="hsl(var(--primary))"
                  strokeWidth={2}
                  strokeDasharray="5 4"
                  dot={{ r: 3, fill: "hsl(var(--primary))", strokeDasharray: "0" }}
                  name="Projected"
                  connectNulls
                />

                {/* Divider between historical and forecast */}
                <ReferenceLine
                  x={bridgePoint.label}
                  stroke="hsl(var(--border))"
                  strokeDasharray="4 2"
                  label={{ value: "Forecast →", position: "insideTopRight", fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </section>

        {/* Projected period table */}
        <section className="section-spacing">
          <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider mb-4">
            Projected Periods
          </h3>
          <div className="bg-card border border-border rounded-lg overflow-x-auto">
            <table className="w-full text-sm min-w-[600px]">
              <thead className="bg-muted/30">
                <tr>
                  {["Period", "Projected Revenue", "Lower Bound (80%)", "Upper Bound (80%)"].map((h) => (
                    <th key={h} className="text-left px-5 py-3 text-xs font-mono text-muted-foreground font-medium">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Array.isArray(forecast.projected_points) && forecast.projected_points.map((p, i) => (
                  <tr key={i} className="border-t border-border/60 hover:bg-muted/20 transition-colors">
                    <td className="px-5 py-3 font-mono text-xs text-muted-foreground">{p.period_label}</td>
                    <td className="px-5 py-3 font-display font-semibold text-foreground">
                      {formatRevenue(p.projected_value)}
                    </td>
                    <td className="px-5 py-3 text-red-400 font-mono text-xs">{formatRevenue(p.lower_bound)}</td>
                    <td className="px-5 py-3 text-emerald-400 font-mono text-xs">{formatRevenue(p.upper_bound)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Technical footnote */}
        <p className="text-[10px] text-muted-foreground font-mono mt-2">
          Method: OLS linear regression · {forecast.confidence_reason}
          {forecast.date_column_used ? ` · Date column: ${forecast.date_column_used}` : " · Row-index mode (no date column)"}
        </p>

      </div>
    </AppLayout>
  );
}
