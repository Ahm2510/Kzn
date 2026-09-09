import { useState, useMemo } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { InsightCard, InsightSeverity } from "@/components/ui/InsightCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Lightbulb, Database, Search } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useLatestCompletedRun } from "@/hooks/useAnalysis";
import { SeveritySeal, SignalTag, type SeverityLevel } from "@/components/ui/SeveritySeal";
import { CountUp } from "@/components/ui/CountUp";
import { Reveal, RevealItem } from "@/components/motion";
import { formatINR, formatINRLakh, formatCount } from "@/lib/format";
import { cn } from "@/lib/utils";

type SeverityFilter = "all" | "high" | "medium" | "low";

export default function Insights() {
  const navigate = useNavigate();
  const { data: run, isLoading, error } = useLatestCompletedRun();

  const [searchTerm, setSearchTerm] = useState("");
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("all");

  const bi = run?.insight_report?.business_insights ?? null;
  const insights = useMemo(() => run?.insight_report?.insights || [], [run]);

  const filteredInsights = useMemo(() => {
    let result = [...insights];
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      result = result.filter(
        (ins) =>
          ins.title.toLowerCase().includes(q) ||
          ins.description.toLowerCase().includes(q) ||
          (ins.driver && ins.driver.toLowerCase().includes(q)) ||
          (ins.action_direction && ins.action_direction.toLowerCase().includes(q))
      );
    }
    if (severityFilter !== "all") {
      result = result.filter((ins) => ins.severity === severityFilter);
    }
    return result;
  }, [insights, searchTerm, severityFilter]);

  if (isLoading) {
    return (
      <AppLayout>
        <div className="page-container">
          <div className="h-8 w-56 rounded bg-muted animate-pulse" />
          <div className="mt-8 space-y-4">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-36 rounded-lg border border-border bg-card animate-pulse" />
            ))}
          </div>
        </div>
      </AppLayout>
    );
  }

  if (error) {
    return (
      <AppLayout>
        <EmptyState
          icon={Lightbulb}
          title="We couldn't load your insights"
          description={(error as Error).message || "The analysis service didn't respond. Refresh to try again."}
          action={<Button variant="outline" onClick={() => window.location.reload()}>Try again</Button>}
          className="h-[calc(100vh-3.5rem)]"
        />
      </AppLayout>
    );
  }

  const churn = bi?.customer_churn_risk;
  const dead = bi?.inventory_health_score;
  const recv = bi?.receivables_risk;
  const hasDistribution =
    (churn?.has_at_risk) || (dead?.dead_stock_count ?? 0) > 0 || (recv?.total_outstanding ?? 0) > 0;

  if (insights.length === 0 && !hasDistribution) {
    return (
      <AppLayout>
        <EmptyState
          icon={Lightbulb}
          title="No findings yet"
          description="Upload a sales or ledger export and Kaizen will surface churn, dead stock, overdue payments, and structural risks."
          action={
            <Button onClick={() => navigate("/datasets")}>
              <Database className="mr-2 h-4 w-4" />
              Upload a dataset
            </Button>
          }
          className="h-[calc(100vh-3.5rem)]"
        />
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="page-container">
        <header className="mb-8">
          <p className="eyebrow">Where your money is leaking</p>
          <h1 className="mt-2 font-display text-2xl font-semibold tracking-tight text-foreground">
            Churn, dead stock &amp; receivables
          </h1>
        </header>

        {/* ── Receivables ───────────────────────────────────────────────── */}
        {recv && (recv.total_outstanding ?? 0) > 0 && (
          <RiskSection
            level={(recv.over_45_amount ?? 0) > 0 ? "overdue" : "slowing"}
            title="Overdue receivables"
            headline={
              <>
                <CountUp value={recv.total_outstanding ?? 0} format={formatINRLakh} className="font-mono font-semibold tabular-nums text-foreground" />
                {" "}outstanding across {formatCount(recv.customer_count ?? 0)} customers
                {recv.aging_available && (recv.over_45_amount ?? 0) > 0 && (
                  <>, <span className="text-signal-overdue">{formatINRLakh(recv.over_45_amount)}</span> over 45 days</>
                )}
              </>
            }
            warning={recv.warning}
            rows={(recv.customers ?? []).slice(0, 8).map((c) => {
              const aged = (c.oldest_unpaid_days ?? 0) >= 45;
              return {
                key: c.customer,
                level: (aged ? "overdue" : "slowing") as SeverityLevel,
                tag: c.aging_bucket ? `${c.aging_bucket} days` : "outstanding",
                name: c.customer,
                meta: c.oldest_unpaid_days != null ? `oldest bill ${c.oldest_unpaid_days}d old` : undefined,
                amount: formatINR(c.outstanding),
              };
            })}
          />
        )}

        {/* ── Dead stock ────────────────────────────────────────────────── */}
        {dead && (dead.dead_stock_count ?? 0) > 0 && (
          <RiskSection
            level="slowing"
            title="Dead & slow-moving stock"
            headline={
              <>
                <CountUp value={dead.total_dead_stock_value ?? 0} format={formatINRLakh} className="font-mono font-semibold tabular-nums text-foreground" />
                {" "}tied up in {formatCount(dead.dead_stock_count ?? 0)} SKUs idle {dead.dead_stock_window_days ?? 60}+ days
              </>
            }
            rows={(dead.dead_stock_skus ?? []).slice(0, 8).map((s) => ({
              key: s.sku,
              level: "slowing" as SeverityLevel,
              tag: `idle ${s.days_inactive}d`,
              name: s.sku,
              meta: `last sold ${s.last_sold}`,
              amount: formatINR(s.value_tied_up),
            }))}
          />
        )}

        {/* ── Customer churn ────────────────────────────────────────────── */}
        {churn && churn.has_at_risk && (
          <RiskSection
            level={(churn.churned_count ?? 0) > 0 ? "overdue" : "slowing"}
            title="Accounts going quiet"
            headline={
              <>
                <CountUp value={churn.revenue_at_risk ?? 0} format={formatINRLakh} className="font-mono font-semibold tabular-nums text-foreground" />
                {" "}of historic revenue at risk across {formatCount((churn.at_risk_count ?? 0) + (churn.churned_count ?? 0))} accounts.
                {" "}Following up is likely to recover revenue.
              </>
            }
            warning={churn.warning}
            rows={(churn.customers ?? [])
              .filter((c) => c.risk === "churned" || c.risk === "at_risk")
              .slice(0, 8)
              .map((c) => ({
                key: c.customer,
                level: (c.risk === "churned" ? "overdue" : "slowing") as SeverityLevel,
                tag: c.risk === "churned" ? "churned" : "at risk",
                name: c.customer,
                meta: `quiet ${c.days_since_last_order}d · ${c.order_count} orders`,
                amount: formatINR(c.total_revenue),
              }))}
          />
        )}

        {/* ── Structural findings ───────────────────────────────────────── */}
        {insights.length > 0 && (
          <section className="mt-12">
            <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <h2 className="eyebrow">Structural findings</h2>
              <div className="flex items-center gap-2">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Search findings"
                    className="h-9 w-48 pl-9 text-sm"
                  />
                </div>
                <div className="flex gap-1">
                  {(["all", "high", "medium", "low"] as SeverityFilter[]).map((f) => (
                    <button
                      key={f}
                      onClick={() => setSeverityFilter(f)}
                      className={cn(
                        "focus-calm rounded-md border px-2.5 py-1.5 text-xs font-medium capitalize transition-colors",
                        severityFilter === f
                          ? "border-primary bg-primary text-primary-foreground"
                          : "border-border bg-card text-muted-foreground hover:text-foreground"
                      )}
                    >
                      {f}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {filteredInsights.length === 0 ? (
              <div className="rounded-lg border border-border bg-card p-10 text-center">
                <p className="text-sm text-muted-foreground">No findings match your filters.</p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-4"
                  onClick={() => { setSearchTerm(""); setSeverityFilter("all"); }}
                >
                  Reset filters
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                {filteredInsights.map((insight, idx) => (
                  <InsightCard
                    key={insight.code ?? idx}
                    title={insight.title}
                    description={insight.description}
                    driver={insight.driver}
                    implication={insight.implication}
                    actionDirection={insight.action_direction}
                    confidence={insight.confidence}
                    confidenceBasis={insight.confidence_basis}
                    severity={insight.severity as InsightSeverity}
                    expandable
                    defaultExpanded={insight.severity === "high"}
                  />
                ))}
              </div>
            )}
          </section>
        )}
      </div>
    </AppLayout>
  );
}

// ─────────────────────────────────────────────────────────────────────────────

interface RiskRowData {
  key: string;
  level: SeverityLevel;
  tag: string;
  name: string;
  meta?: string;
  amount: string;
}

function RiskSection({
  level,
  title,
  headline,
  rows,
  warning,
}: {
  level: SeverityLevel;
  title: string;
  headline: React.ReactNode;
  rows: RiskRowData[];
  warning?: string | null;
}) {
  return (
    <section className="mb-8">
      <div className="mb-3 flex items-start gap-3">
        <SeveritySeal level={level} size="lg" pulse={level === "overdue"} />
        <div>
          <h2 className="font-display text-lg font-semibold tracking-tight text-foreground">{title}</h2>
          <p className="mt-0.5 text-sm leading-relaxed text-muted-foreground">{headline}</p>
        </div>
      </div>

      <Reveal className="divide-y divide-border overflow-hidden rounded-lg border border-border bg-card" stagger={0.04}>
        {rows.map((r) => (
          <RevealItem key={r.key}>
            <div className="flex items-center gap-3 px-5 py-3 transition-colors hover:bg-muted/40">
              <SeveritySeal level={r.level} size="sm" />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="truncate text-sm font-medium text-foreground">{r.name}</span>
                  <SignalTag level={r.level}>{r.tag}</SignalTag>
                </div>
                {r.meta && <p className="mt-0.5 text-xs text-muted-foreground">{r.meta}</p>}
              </div>
              <span className="shrink-0 font-mono text-sm font-semibold tabular-nums text-foreground">{r.amount}</span>
            </div>
          </RevealItem>
        ))}
      </Reveal>

      {warning && <p className="mt-2 text-xs text-signal-slowing">{warning}</p>}
    </section>
  );
}
