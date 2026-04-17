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
        {bi?.products_to_watch && Array.isArray(bi.products_to_watch) && bi.products_to_watch.length > 0 && (
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
        )}
      </div>
    </AppLayout>
  );
}
