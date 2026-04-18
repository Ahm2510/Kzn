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
 
        {bi?.enhanced_executive_summary && bi.enhanced_executive_summary.narrative && (
          <section className="section-spacing">
            <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider mb-4">
              Enhanced Executive Summary
            </h3>
            <div className="bg-card border border-border rounded-lg p-6 space-y-4">
              <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
                {bi.enhanced_executive_summary.overall_sentiment && (
                  <span>
                    Outlook:{" "}
                    <span className={`font-mono font-bold ${
                      bi.enhanced_executive_summary.overall_sentiment === "positive" ? "text-emerald-600" :
                      bi.enhanced_executive_summary.overall_sentiment === "negative" ? "text-red-500" :
                      bi.enhanced_executive_summary.overall_sentiment === "mixed" ? "text-amber-500" :
                      "text-muted-foreground"
                    }`}>
                      {bi.enhanced_executive_summary.overall_sentiment.toUpperCase()}
                    </span>
                  </span>
                )}
                {bi.enhanced_executive_summary.confidence && (
                  <span>Confidence: <span className="font-mono">{bi.enhanced_executive_summary.confidence.toUpperCase()}</span></span>
                )}
                {bi.enhanced_executive_summary.data_coverage && (
                  <span>Coverage: <span className="font-mono">{bi.enhanced_executive_summary.data_coverage.replace(/_/g, " ").toUpperCase()}</span></span>
                )}
              </div>
 
              <p className="text-sm text-foreground leading-relaxed">
                {bi.enhanced_executive_summary.narrative}
              </p>
 
              {bi.enhanced_executive_summary.key_positives && bi.enhanced_executive_summary.key_positives.length > 0 && (
                <div className="pt-3 border-t border-border/60">
                  <p className="text-xs font-medium text-emerald-600 mb-2">Key Strengths</p>
                  <div className="space-y-1">
                    {bi.enhanced_executive_summary.key_positives.slice(0, 4).map((p, i) => (
                      <p key={i} className="text-xs text-foreground/80">+ {p}</p>
                    ))}
                  </div>
                </div>
              )}
 
              {bi.enhanced_executive_summary.key_risks && bi.enhanced_executive_summary.key_risks.length > 0 && (
                <div className="pt-3 border-t border-border/60">
                  <p className="text-xs font-medium text-red-500 mb-2">Key Risks</p>
                  <div className="space-y-1">
                    {bi.enhanced_executive_summary.key_risks.slice(0, 4).map((r, i) => (
                      <p key={i} className="text-xs text-foreground/80">- {r}</p>
                    ))}
                  </div>
                </div>
              )}
 
              {bi.enhanced_executive_summary.watchpoints && bi.enhanced_executive_summary.watchpoints.length > 0 && (
                <div className="pt-3 border-t border-border/60">
                  <p className="text-xs font-medium text-muted-foreground mb-2">Leadership Watchpoints</p>
                  <div className="space-y-1">
                    {bi.enhanced_executive_summary.watchpoints.slice(0, 4).map((w, i) => (
                      <p key={i} className="text-xs text-foreground/80">{w}</p>
                    ))}
                  </div>
                </div>
              )}
 
              {bi.enhanced_executive_summary.warning && (
                <p className="text-xs text-amber-500 bg-amber-500/5 border border-amber-500/20 rounded px-3 py-2">
                  {bi.enhanced_executive_summary.warning}
                </p>
              )}
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

        {bi?.mom_commentary && bi.mom_commentary.commentary && (
          <section className="section-spacing">
            <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider mb-4">
              Period-over-Period Commentary
            </h3>
            <div className="bg-card border border-border rounded-lg p-6 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex flex-wrap gap-2">
                  <StatusBadge 
                    status="complete" 
                    label={bi.mom_commentary.direction?.toUpperCase() || "FLAT"} 
                  />
                  {bi.mom_commentary.magnitude && bi.mom_commentary.magnitude !== "no_baseline" && (
                    <StatusBadge 
                      status="complete" 
                      label={bi.mom_commentary.magnitude.toUpperCase()} 
                    />
                  )}
                  {bi.mom_commentary.is_meaningful && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-indigo-500/10 text-indigo-500 border border-indigo-500/20">
                      MEANINGFUL
                    </span>
                  )}
                </div>
                <div className="flex gap-4 text-[10px] font-mono whitespace-nowrap">
                   {bi.mom_commentary.revenue_baseline != null && (
                     <div className="text-muted-foreground">
                       BASELINE: <span className="text-foreground">${bi.mom_commentary.revenue_baseline.toLocaleString()}</span>
                     </div>
                   )}
                   <div className="text-muted-foreground">
                     CURRENT: <span className="text-foreground">${bi.mom_commentary.revenue_current?.toLocaleString()}</span>
                   </div>
                   {bi.mom_commentary.percent_change != null && (
                     <div className="text-muted-foreground">
                       CHANGE: <span className={bi.mom_commentary.percent_change >= 0 ? "text-emerald-500" : "text-red-500"}>
                         {bi.mom_commentary.percent_change >= 0 ? "+" : ""}{bi.mom_commentary.percent_change.toFixed(1)}%
                       </span>
                     </div>
                   )}
                </div>
              </div>

              <div className="pt-2 border-t border-border/60">
                <p className="text-sm text-foreground leading-relaxed italic">
                  "{bi.mom_commentary.commentary}"
                </p>
              </div>

              {bi.mom_commentary.interpretation && (
                <div className="p-3 bg-muted/30 border border-border/50 rounded-md">
                  <p className="text-xs text-foreground">
                    <span className="font-bold text-primary mr-1">Interpretation:</span>
                    {bi.mom_commentary.interpretation}
                  </p>
                </div>
              )}

              {bi.mom_commentary.driver_hint && (
                <p className="text-xs text-muted-foreground">
                  <span className="font-medium">Potential Driver:</span> {bi.mom_commentary.driver_hint}
                </p>
              )}

              <div className="flex items-center justify-between pt-2">
                <p className="text-[10px] text-muted-foreground font-mono">
                  Confidence: {bi.mom_commentary.confidence?.toUpperCase()} (n={bi.mom_commentary.sample_size?.toLocaleString()})
                </p>
                {bi.mom_commentary.warning && (
                  <span className="text-[10px] text-amber-500 font-medium">
                    ⚠ {bi.mom_commentary.warning}
                  </span>
                )}
              </div>
            </div>
          </section>
        )}

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

        {bi?.revenue_stability_index && (
          <section className="section-spacing">
            <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider mb-4">
              Revenue Stability Index
            </h3>
            <div className="bg-card border border-border rounded-lg p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-3xl font-display font-bold text-foreground">
                    {Math.round(bi.revenue_stability_index.score)}
                  </span>
                  <span className="text-sm text-muted-foreground ml-1">/100</span>
                </div>
                <StatusBadge status="complete" label={bi.revenue_stability_index.label} />
              </div>
              <p className="text-sm text-foreground leading-relaxed">
                {bi.revenue_stability_index.explanation}
              </p>
              {bi.revenue_stability_index.contributing_factors &&
                bi.revenue_stability_index.contributing_factors.length > 0 && (
                  <div className="space-y-1 pt-2 border-t border-border/60">
                    {bi.revenue_stability_index.contributing_factors.map(
                      (f: string, i: number) => (
                        <p key={i} className="text-xs text-muted-foreground">
                          - {f}
                        </p>
                      )
                    )}
                  </div>
                )}
              {bi.revenue_stability_index.warning && (
                <p className="text-xs text-amber-500 bg-amber-500/5 border border-amber-500/20 rounded px-3 py-2">
                  ⚠ {bi.revenue_stability_index.warning}
                </p>
              )}
              <p className="text-xs text-muted-foreground">
                Confidence:{" "}
                <span className="font-mono">
                  {(bi.revenue_stability_index.confidence ?? "").toUpperCase()}
                </span>
              </p>
            </div>
          </section>
        )}

        {bi?.inventory_health_score && (
          <section className="section-spacing">
            <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider mb-4">
              Inventory Health Score
            </h3>
            <div className="bg-card border border-border rounded-lg p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-3xl font-display font-bold text-foreground">
                    {Math.round(bi.inventory_health_score.score)}
                  </span>
                  <span className="text-sm text-muted-foreground ml-1">/100</span>
                </div>
                <StatusBadge status="complete" label={bi.inventory_health_score.label} />
              </div>
              <p className="text-sm text-foreground leading-relaxed">
                {bi.inventory_health_score.explanation}
              </p>
              {bi.inventory_health_score.contributing_factors &&
                bi.inventory_health_score.contributing_factors.length > 0 && (
                  <div className="space-y-1 pt-2 border-t border-border/60">
                    {bi.inventory_health_score.contributing_factors.map(
                      (f: string, i: number) => (
                        <p key={i} className="text-xs text-muted-foreground">
                          - {f}
                        </p>
                      )
                    )}
                  </div>
                )}
              {bi.inventory_health_score.watchlist &&
                bi.inventory_health_score.watchlist.length > 0 && (
                  <div className="pt-2 border-t border-border/60">
                    <p className="text-xs text-muted-foreground font-medium mb-1">
                      SKUs to review:
                    </p>
                    <p className="text-xs text-foreground">
                      {bi.inventory_health_score.watchlist.join(", ")}
                    </p>
                  </div>
                )}
              {bi.inventory_health_score.warning && (
                <p className="text-xs text-amber-500 bg-amber-500/5 border border-amber-500/20 rounded px-3 py-2">
                  ⚠ {bi.inventory_health_score.warning}
                </p>
              )}
              <p className="text-xs text-muted-foreground">
                Confidence:{" "}
                <span className="font-mono">
                  {(bi.inventory_health_score.confidence ?? "").toUpperCase()}
                </span>
                {bi.inventory_health_score.confidence_reason ? (
                  <span> — {bi.inventory_health_score.confidence_reason}</span>
                ) : bi.inventory_health_score.data_source ? (
                  <span> — based on {bi.inventory_health_score.data_source}</span>
                ) : null}
              </p>
            </div>
          </section>
        )}

        {bi?.early_warning_alerts &&
          bi.early_warning_alerts.alerts &&
          bi.early_warning_alerts.alerts.length > 0 && (
          <section className="section-spacing">
            <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider mb-4">
              Early Warning Alerts
              {bi.early_warning_alerts.has_critical && (
                <span className="ml-2 text-red-500 font-bold text-[10px] bg-red-500/10 border border-red-500/20 rounded px-1.5 py-0.5">
                  CRITICAL
                </span>
              )}
              {!bi.early_warning_alerts.has_critical && bi.early_warning_alerts.has_high && (
                <span className="ml-2 text-amber-500 font-bold text-[10px] bg-amber-500/10 border border-amber-500/20 rounded px-1.5 py-0.5">
                  HIGH
                </span>
              )}
            </h3>
            <div className="space-y-3">
              {bi.early_warning_alerts.alerts.map((alert, idx) => {
                const sevColors: Record<string, string> = {
                  critical: "border-red-500/40 bg-red-500/5",
                  high: "border-amber-500/40 bg-amber-500/5",
                  medium: "border-yellow-500/30 bg-yellow-500/5",
                  low: "border-border bg-card",
                };
                const sevTextColors: Record<string, string> = {
                  critical: "text-red-500",
                  high: "text-amber-500",
                  medium: "text-yellow-600",
                  low: "text-muted-foreground",
                };
                const borderClass = sevColors[alert.severity] || sevColors.low;
                const textClass = sevTextColors[alert.severity] || sevTextColors.low;
 
                return (
                  <div
                    key={alert.alert_code + idx}
                    className={`border rounded-lg p-4 space-y-2 ${borderClass}`}
                  >
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-bold font-mono uppercase ${textClass}`}>
                        {alert.severity}
                      </span>
                      <span className="text-sm font-medium text-foreground">
                        {alert.title}
                      </span>
                    </div>
                    <p className="text-xs text-foreground/80 leading-relaxed">
                      {alert.description}
                    </p>
                    {alert.driver && (
                      <p className="text-xs text-muted-foreground">
                        <span className="font-medium">Driver:</span> {alert.driver}
                      </p>
                    )}
                    {alert.action_direction && (
                      <p className="text-xs text-primary">
                        <span className="font-medium">Action:</span> {alert.action_direction}
                      </p>
                    )}
                    {alert.confidence && (
                      <p className="text-[10px] text-muted-foreground font-mono">
                        Confidence: {alert.confidence.toUpperCase()}
                        {alert.confidence_basis && <span> — {alert.confidence_basis}</span>}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        )}
 
        {bi?.cohort_product_performance &&
          bi.cohort_product_performance.cohorts &&
          bi.cohort_product_performance.cohorts.length > 0 && (
          <section className="section-spacing">
            <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider mb-4">
              Product Cohort Performance
              {bi.cohort_product_performance.has_declining && (
                <span className="ml-2 text-red-500 font-bold text-[10px] bg-red-500/10 border border-red-500/20 rounded px-1.5 py-0.5">
                  DECLINING
                </span>
              )}
            </h3>
            {bi.cohort_product_performance.cohort_basis && (
              <p className="text-xs text-muted-foreground mb-3">
                Grouped by: <span className="font-mono">{bi.cohort_product_performance.cohort_basis.replace(/_/g, " ")}</span>
              </p>
            )}
            <div className="space-y-3">
              {bi.cohort_product_performance.cohorts.map((cohort, idx) => {
                const tierColors: Record<string, string> = {
                  top_performer: "border-emerald-500/40 bg-emerald-500/5",
                  stable_performer: "border-border bg-card",
                  underperformer: "border-amber-500/30 bg-amber-500/5",
                  declining_cohort: "border-red-500/40 bg-red-500/5",
                  insufficient_data: "border-border bg-muted/30",
                };
                const tierTextColors: Record<string, string> = {
                  top_performer: "text-emerald-600",
                  stable_performer: "text-foreground",
                  underperformer: "text-amber-600",
                  declining_cohort: "text-red-500",
                  insufficient_data: "text-muted-foreground",
                };
                const borderClass = tierColors[cohort.performance_tier] || tierColors.stable_performer;
                const textClass = tierTextColors[cohort.performance_tier] || tierTextColors.stable_performer;
 
                return (
                  <div
                    key={cohort.cohort_label + idx}
                    className={`border rounded-lg p-4 space-y-2 ${borderClass}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] font-bold font-mono uppercase ${textClass}`}>
                          {cohort.performance_tier.replace(/_/g, " ")}
                        </span>
                        <span className="text-sm font-medium text-foreground">
                          {cohort.cohort_label}
                        </span>
                      </div>
                      <span className="text-xs font-mono text-muted-foreground">
                        {cohort.revenue_share_pct.toFixed(1)}% rev
                      </span>
                    </div>
                    <div className="flex gap-4 text-xs text-muted-foreground">
                      <span>{cohort.product_count} products</span>
                      <span>{cohort.transaction_count.toLocaleString()} txns</span>
                      {cohort.period_growth_pct != null && (
                        <span className={cohort.period_growth_pct >= 0 ? "text-emerald-600" : "text-red-500"}>
                          {cohort.period_growth_pct >= 0 ? "+" : ""}{cohort.period_growth_pct.toFixed(1)}% growth
                        </span>
                      )}
                      <span>Stability: {cohort.stability}</span>
                    </div>
                    <p className="text-xs text-foreground/80 leading-relaxed">
                      {cohort.explanation}
                    </p>
                    {cohort.warning && (
                      <p className="text-xs text-amber-500 bg-amber-500/5 border border-amber-500/20 rounded px-2 py-1">
                        {cohort.warning}
                      </p>
                    )}
                    <p className="text-[10px] text-muted-foreground font-mono">
                      Confidence: {cohort.confidence.toUpperCase()}
                    </p>
                  </div>
                );
              })}
            </div>
            {bi.cohort_product_performance.warning && (
              <p className="text-xs text-amber-500 mt-3">
                {bi.cohort_product_performance.warning}
              </p>
            )}
          </section>
        )}
 
        {bi?.customer_segmentation &&
          bi.customer_segmentation.segments &&
          bi.customer_segmentation.segments.length > 0 && (
          <section className="section-spacing">
            <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider mb-4">
              Customer Segmentation
              {bi.customer_segmentation.has_at_risk && (
                <span className="ml-2 text-amber-500 font-bold text-[10px] bg-amber-500/10 border border-amber-500/20 rounded px-1.5 py-0.5">
                  AT RISK
                </span>
              )}
              {bi.customer_segmentation.has_declining && !bi.customer_segmentation.has_at_risk && (
                <span className="ml-2 text-red-500 font-bold text-[10px] bg-red-500/10 border border-red-500/20 rounded px-1.5 py-0.5">
                  DECLINING
                </span>
              )}
            </h3>
            <div className="flex gap-4 text-xs text-muted-foreground mb-3">
              {bi.customer_segmentation.segment_basis && (
                <span>Method: <span className="font-mono">{bi.customer_segmentation.segment_basis.toUpperCase()}</span></span>
              )}
              {bi.customer_segmentation.total_customers != null && (
                <span>Customers: <span className="font-mono">{bi.customer_segmentation.total_customers.toLocaleString()}</span></span>
              )}
              <span>Segments: <span className="font-mono">{bi.customer_segmentation.segments.length}</span></span>
            </div>
            <div className="space-y-3">
              {bi.customer_segmentation.segments.map((seg, idx) => {
                const tierColors: Record<string, string> = {
                  high_value: "border-emerald-500/40 bg-emerald-500/5",
                  growing: "border-blue-500/40 bg-blue-500/5",
                  stable_value: "border-border bg-card",
                  at_risk: "border-amber-500/40 bg-amber-500/5",
                  declining: "border-red-500/40 bg-red-500/5",
                  insufficient_data: "border-border bg-muted/30",
                };
                const tierTextColors: Record<string, string> = {
                  high_value: "text-emerald-600",
                  growing: "text-blue-600",
                  stable_value: "text-foreground",
                  at_risk: "text-amber-600",
                  declining: "text-red-500",
                  insufficient_data: "text-muted-foreground",
                };
                const borderClass = tierColors[seg.tier] || tierColors.stable_value;
                const textClass = tierTextColors[seg.tier] || tierTextColors.stable_value;
 
                return (
                  <div
                    key={seg.segment_label + idx}
                    className={`border rounded-lg p-4 space-y-2 ${borderClass}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] font-bold font-mono uppercase ${textClass}`}>
                          {seg.tier.replace(/_/g, " ")}
                        </span>
                        <span className="text-sm font-medium text-foreground">
                          {seg.segment_label}
                        </span>
                      </div>
                      <span className="text-xs font-mono text-muted-foreground">
                        {seg.revenue_share_pct.toFixed(1)}% rev
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
                      <span>{seg.customer_count.toLocaleString()} customers</span>
                      {seg.avg_order_frequency != null && (
                        <span>Freq: {seg.avg_order_frequency.toFixed(1)}</span>
                      )}
                      {seg.avg_recency_days != null && (
                        <span>Recency: {seg.avg_recency_days.toFixed(0)}d</span>
                      )}
                      {seg.period_growth_pct != null && (
                        <span className={seg.period_growth_pct >= 0 ? "text-emerald-600" : "text-red-500"}>
                          {seg.period_growth_pct >= 0 ? "+" : ""}{seg.period_growth_pct.toFixed(1)}% growth
                        </span>
                      )}
                      <span>Stability: {seg.stability}</span>
                    </div>
                    <p className="text-xs text-foreground/80 leading-relaxed">
                      {seg.explanation}
                    </p>
                    {seg.warning && (
                      <p className="text-xs text-amber-500 bg-amber-500/5 border border-amber-500/20 rounded px-2 py-1">
                        {seg.warning}
                      </p>
                    )}
                    <p className="text-[10px] text-muted-foreground font-mono">
                      Confidence: {seg.confidence.toUpperCase()}
                    </p>
                  </div>
                );
              })}
            </div>
            {bi.customer_segmentation.warning && (
              <p className="text-xs text-amber-500 mt-3">
                {bi.customer_segmentation.warning}
              </p>
            )}
          </section>
        )}
 
        {bi?.concentration_risk_dashboard &&
          bi.concentration_risk_dashboard.dimensions &&
          bi.concentration_risk_dashboard.dimensions.length > 0 && (
          <section className="section-spacing">
            <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider mb-4">
              Concentration Risk Dashboard
              {bi.concentration_risk_dashboard.has_critical && (
                <span className="ml-2 text-red-500 font-bold text-[10px] bg-red-500/10 border border-red-500/20 rounded px-1.5 py-0.5">
                  CRITICAL
                </span>
              )}
              {!bi.concentration_risk_dashboard.has_critical && bi.concentration_risk_dashboard.has_high && (
                <span className="ml-2 text-amber-500 font-bold text-[10px] bg-amber-500/10 border border-amber-500/20 rounded px-1.5 py-0.5">
                  HIGH
                </span>
              )}
            </h3>
            <div className="flex gap-4 text-xs text-muted-foreground mb-3">
              <span>Overall: <span className="font-mono font-bold">{bi.concentration_risk_dashboard.overall_risk?.toUpperCase()}</span></span>
              <span>Score: <span className="font-mono">{bi.concentration_risk_dashboard.overall_score?.toFixed(1)}/100</span></span>
              <span>Dimensions: <span className="font-mono">{bi.concentration_risk_dashboard.dimensions.length}</span></span>
            </div>
            <div className="space-y-3">
              {bi.concentration_risk_dashboard.dimensions.map((dim, idx) => {
                const riskColors: Record<string, string> = {
                  critical: "border-red-500/40 bg-red-500/5",
                  high: "border-amber-500/40 bg-amber-500/5",
                  moderate: "border-yellow-500/30 bg-yellow-500/5",
                  low: "border-emerald-500/30 bg-emerald-500/5",
                };
                const riskTextColors: Record<string, string> = {
                  critical: "text-red-500",
                  high: "text-amber-500",
                  moderate: "text-yellow-600",
                  low: "text-emerald-600",
                };
                const borderClass = riskColors[dim.risk_level] || riskColors.low;
                const textClass = riskTextColors[dim.risk_level] || riskTextColors.low;
 
                return (
                  <div
                    key={dim.dimension + idx}
                    className={`border rounded-lg p-4 space-y-2 ${borderClass}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] font-bold font-mono uppercase ${textClass}`}>
                          {dim.risk_level}
                        </span>
                        <span className="text-sm font-medium text-foreground capitalize">
                          {dim.dimension} Concentration
                        </span>
                      </div>
                      <span className="text-xs font-mono text-muted-foreground">
                        {dim.composite_score.toFixed(1)}/100
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
                      <span>HHI: {dim.hhi.toFixed(0)}</span>
                      <span>Gini: {dim.gini.toFixed(2)}</span>
                      <span>Top 1: {dim.top_1_share_pct.toFixed(1)}%</span>
                      <span>Top 5: {dim.top_5_share_pct.toFixed(1)}%</span>
                      <span>{dim.contributor_count} contributors</span>
                      {dim.trend && (
                        <span className={dim.trend === "decreasing" ? "text-emerald-600" : dim.trend === "increasing" ? "text-red-500" : "text-muted-foreground"}>
                          Trend: {dim.trend}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-foreground/80 leading-relaxed">
                      {dim.explanation}
                    </p>
                    {dim.top_contributors && dim.top_contributors.length > 0 && (
                      <div className="pt-1">
                        <p className="text-[10px] text-muted-foreground font-medium mb-1">Top contributors:</p>
                        <div className="flex flex-wrap gap-2">
                          {dim.top_contributors.slice(0, 5).map((c, ci) => (
                            <span key={ci} className="text-[10px] font-mono bg-muted/50 border border-border rounded px-1.5 py-0.5">
                              {c.name.length > 30 ? c.name.slice(0, 30) + "..." : c.name} ({c.share_pct.toFixed(1)}%)
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {dim.warning && (
                      <p className="text-xs text-amber-500 bg-amber-500/5 border border-amber-500/20 rounded px-2 py-1">
                        {dim.warning}
                      </p>
                    )}
                    <p className="text-[10px] text-muted-foreground font-mono">
                      Confidence: {dim.confidence.toUpperCase()}
                    </p>
                  </div>
                );
              })}
            </div>
            {bi.concentration_risk_dashboard.warning && (
              <p className="text-xs text-amber-500 mt-3">
                {bi.concentration_risk_dashboard.warning}
              </p>
            )}
          </section>
        )}
 
        {bi?.data_quality && (
          <section className="section-spacing">
            <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider mb-4">
              Data Quality Summary
            </h3>
            <div className="bg-card border border-border rounded-lg p-6 space-y-4">
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
                      <span className="text-muted-foreground">Fields Detected:</span>
                      <div className="flex flex-wrap gap-1.5 mt-1">
                        {Object.keys(bi.data_quality.schema_detected.detected_columns).sort().map(field => (
                          <span key={field} className="px-1.5 py-0.5 bg-muted rounded text-[10px] font-mono text-foreground">
                            {field.toUpperCase()}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {bi.data_quality.date_columns_parsed && bi.data_quality.date_columns_parsed.length > 0 && (
                    <div className="text-sm">
                      <span className="text-muted-foreground">Timeline:</span>
                      <p className="text-xs text-foreground">
                        Parsed from: <span className="font-mono">{bi.data_quality.date_columns_parsed.join(", ")}</span>
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {(bi.data_quality.warnings && bi.data_quality.warnings.length > 0) && (
                <div className="pt-3 border-t border-border/60">
                  <p className="text-[10px] font-bold text-amber-500 uppercase tracking-tight mb-2">Preprocessing Warnings</p>
                  <div className="space-y-1">
                    {bi.data_quality.warnings.map((w, i) => (
                      <p key={i} className="text-xs text-amber-600/90 italic">⚠ {w}</p>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </section>
        )}
 
        {/* Business Insight Detail Sections */}
        {hasBI && (



          <section className="section-spacing space-y-6">
            {[
              { label: "Trend Analysis", data: bi?.trend },
              { label: "Revenue Stability", data: bi?.stability },
              { label: "Revenue Efficiency", data: bi?.efficiency },
              { label: "Revenue Concentration", data: bi?.concentration },
            ]
              .filter((s) => s.data && (s.data.driver || s.data.implication || s.data.action_direction))
              .map((section) => (
                <div key={section.label} className="bg-card border border-border rounded-lg p-6 space-y-3">
                  <h4 className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
                    {section.label}
                  </h4>
                  {section.data?.description && (
                    <p className="text-sm text-foreground leading-relaxed">{section.data.description}</p>
                  )}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 border-t border-border/60">
                    {section.data?.driver && (
                      <div className="text-xs">
                        <span className="text-muted-foreground">Driver: </span>
                        <span className="text-foreground">{section.data.driver}</span>
                      </div>
                    )}
                    {section.data?.implication && (
                      <div className="text-xs">
                        <span className="text-muted-foreground">Implication: </span>
                        <span className="text-foreground">{section.data.implication}</span>
                      </div>
                    )}
                    {section.data?.action_direction && (
                      <div className="text-xs">
                        <span className="text-muted-foreground">Action: </span>
                        <span className="text-primary font-medium">{section.data.action_direction}</span>
                      </div>
                    )}
                  </div>
                  {section.data?.confidence && (
                    <p className="text-xs text-muted-foreground mt-2">
                      Confidence: <span className="font-mono">{String(section.data.confidence).toUpperCase()}</span>
                      {section.data.confidence_basis && (
                        <span> — {section.data.confidence_basis}</span>
                      )}
                    </p>
                  )}
                </div>
              ))}
          </section>
        )}

        {/* Products to Watch */}
        {bi?.enhanced_products_to_watch && bi.enhanced_products_to_watch.products && bi.enhanced_products_to_watch.products.length > 0 ? (
          <section className="section-spacing">
            <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider mb-4">
              Products to Watch (Enhanced)
              {bi.enhanced_products_to_watch.has_declining && (
                <span className="ml-2 text-red-500 font-bold text-[10px] bg-red-500/10 border border-red-500/20 rounded px-1.5 py-0.5">
                  DECLINING DETECTED
                </span>
              )}
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {bi.enhanced_products_to_watch.products.map((p, idx) => {
                const statusColors: Record<string, string> = {
                  declining: "text-red-500 bg-red-500/5 border-red-500/20",
                  unstable: "text-amber-500 bg-amber-500/5 border-amber-500/20",
                  watch: "text-blue-500 bg-blue-500/5 border-blue-500/20",
                  improving: "text-emerald-500 bg-emerald-500/5 border-emerald-500/20",
                  low_confidence: "text-muted-foreground bg-muted/50 border-border",
                };
                return (
                  <div key={idx} className="bg-card border border-border rounded-lg p-5 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-bold text-foreground truncate max-w-[70%]">{p.product}</span>
                      <span className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded border ${statusColors[p.status] || statusColors.watch}`}>
                        {p.status.toUpperCase()}
                      </span>
                    </div>
                    <div className="flex gap-4 text-[10px] font-mono text-muted-foreground">
                      <span>Share: {p.revenue_share_pct.toFixed(1)}%</span>
                      {p.trend_direction && p.trend_direction !== "insufficient_data" && (
                        <span>Trend: {p.trend_direction.toUpperCase()}</span>
                      )}
                      <span>Conf: {p.confidence.toUpperCase()}</span>
                    </div>
                    <p className="text-xs text-foreground/80 leading-relaxed">
                      {p.reason}
                    </p>
                    {p.action_direction && (
                      <p className="text-xs text-primary font-medium pt-2 border-t border-border/40">
                        {p.action_direction}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
            {bi.enhanced_products_to_watch.warning && (
              <p className="text-xs text-amber-500 mt-3">⚠ {bi.enhanced_products_to_watch.warning}</p>
            )}
          </section>
        ) : (
          bi?.products_to_watch && Array.isArray(bi.products_to_watch) && bi.products_to_watch.length > 0 && (
            <section className="section-spacing">
              <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider mb-4">
                Products to Watch
              </h3>
              <div className="bg-card border border-border rounded-lg p-6">
                <ul className="list-disc pl-5 space-y-1">
                  {bi.products_to_watch.map((p: string, idx: number) => (
                    <li key={idx} className="text-sm text-foreground">{p}</li>
                  ))}
                </ul>
                <p className="text-xs text-muted-foreground mt-3">
                  These products are underperforming relative to the portfolio — consider reviewing pricing, availability, or positioning.
                </p>
              </div>
            </section>
          )
        )}
      </div>
    </AppLayout>
  );
}
