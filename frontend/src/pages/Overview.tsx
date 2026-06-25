import { AppLayout } from "@/components/layout/AppLayout";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/button";
import { Database, LayoutDashboard, ArrowRight, CheckCircle2, TriangleAlert } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useLatestCompletedRun } from "@/hooks/useAnalysis";
import { AttentionLedger, type LedgerItem } from "@/components/ledger/AttentionLedger";
import { CountUp } from "@/components/ui/CountUp";
import { Reveal, RevealItem } from "@/components/motion";
import { formatINRLakh } from "@/lib/format";
import { cn } from "@/lib/utils";

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning.";
  if (h < 17) return "Good afternoon.";
  return "Good evening.";
}

function OverviewSkeleton() {
  return (
    <div className="page-container">
      <div className="h-5 w-40 rounded bg-muted animate-pulse" />
      <div className="mt-3 h-8 w-72 rounded bg-muted animate-pulse" />
      <div className="mt-8 space-y-px overflow-hidden rounded-lg border border-border">
        {[0, 1, 2].map((i) => (
          <div key={i} className="flex items-center gap-4 bg-card px-5 py-5">
            <div className="h-7 w-7 rounded-md bg-muted animate-pulse" />
            <div className="flex-1 space-y-2">
              <div className="h-3 w-20 rounded bg-muted animate-pulse" />
              <div className="h-4 w-2/3 rounded bg-muted animate-pulse" />
            </div>
            <div className="h-5 w-16 rounded bg-muted animate-pulse" />
          </div>
        ))}
      </div>
      <div className="mt-6 h-20 rounded-lg border border-border bg-card animate-pulse" />
    </div>
  );
}

export default function Overview() {
  const navigate = useNavigate();
  const { data: run, isLoading, error } = useLatestCompletedRun();

  if (isLoading) {
    return (
      <AppLayout>
        <OverviewSkeleton />
      </AppLayout>
    );
  }

  if (error) {
    return (
      <AppLayout>
        <EmptyState
          icon={LayoutDashboard}
          title="We couldn't load your overview"
          description={
            (error as Error).message ||
            "The analysis service didn't respond. Refresh to try again, or re-run the dataset from Datasets."
          }
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

  if (!run || !run.insight_report) {
    return (
      <AppLayout>
        <EmptyState
          icon={Database}
          title="Nothing to show yet"
          description="Upload a sales or ledger export and Kaizen will surface who's churning, what stock is dead, and which payments are overdue."
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

  const report = run.insight_report;
  const bi = report?.business_insights || null;

  // ── Build the attention ledger from the action list + structured amounts ──
  const amountFor: Record<string, number | undefined> = {
    churn: bi?.customer_churn_risk?.revenue_at_risk,
    dead_stock: bi?.inventory_health_score?.total_dead_stock_value ?? undefined,
    receivables: bi?.receivables_risk?.total_outstanding,
  };
  const tagFor: Record<string, string> = {
    receivables: "Overdue",
    churn: "Gone quiet",
    dead_stock: "Dead stock",
  };
  const ledgerItems: LedgerItem[] = (bi?.action_list ?? []).map((a, i) => ({
    id: `${a.category}-${i}`,
    level: a.category === "receivables" ? "overdue" : "slowing",
    tag: tagFor[a.category] ?? a.category.replace(/_/g, " "),
    headline: a.headline,
    detail: a.detail ?? undefined,
    amount: amountFor[a.category],
  }));

  const headlineFigures = [
    { label: "Outstanding", value: bi?.receivables_risk?.total_outstanding, sub: bi?.receivables_risk?.customer_count ? `${bi.receivables_risk.customer_count} customers` : undefined },
    { label: "Dead stock", value: bi?.inventory_health_score?.total_dead_stock_value ?? undefined, sub: bi?.inventory_health_score?.dead_stock_count ? `${bi.inventory_health_score.dead_stock_count} SKUs` : undefined },
    { label: "Revenue at risk", value: bi?.customer_churn_risk?.revenue_at_risk, sub: bi?.customer_churn_risk ? `${(bi.customer_churn_risk.at_risk_count ?? 0) + (bi.customer_churn_risk.churned_count ?? 0)} shops` : undefined },
  ].filter((f) => typeof f.value === "number" && (f.value as number) > 0) as { label: string; value: number; sub?: string }[];

  const schemaWarnings = bi?.schema_warnings ?? [];

  const signals = [
    { label: "Trend", value: bi?.trend?.direction || report.trend_direction },
    { label: "Stability", value: bi?.stability?.category || report.stability },
    { label: "Concentration", value: bi?.concentration?.risk_level || report.concentration_risk },
    { label: "Efficiency", value: bi?.efficiency?.signal || report.efficiency_signal },
  ].filter((s) => s.value);

  const summary =
    bi?.enhanced_executive_summary?.narrative || report.summary || report.executive_summary || "";

  const stateLine =
    ledgerItems.length > 0
      ? `${ledgerItems.length} ${ledgerItems.length === 1 ? "thing needs" : "things need"} your attention today.`
      : "Nothing urgent today. Here's where the business stands.";

  return (
    <AppLayout>
      <div className="page-container">
        {/* Greeting + one-line state of the business */}
        <header className="mb-8">
          <p className="eyebrow">{new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" })}</p>
          <h1 className="mt-2 font-display text-2xl font-semibold tracking-tight text-foreground">
            {greeting()} <span className="text-muted-foreground">{stateLine}</span>
          </h1>
        </header>

        {/* Schema coverage warnings — an honest, designed notice, not a silent gap */}
        {schemaWarnings.length > 0 && (
          <div className="mb-8 rounded-lg border border-signal-slowing/30 bg-signal-slowing/[0.06] p-4">
            <div className="flex items-start gap-2.5">
              <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-signal-slowing" aria-hidden />
              <div>
                <p className="text-sm font-medium text-foreground">Some columns weren't detected</p>
                <ul className="mt-1.5 space-y-1">
                  {schemaWarnings.slice(0, 4).map((w, i) => (
                    <li key={i} className="text-xs leading-relaxed text-muted-foreground">{w}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* HERO — the attention ledger */}
        <section className="mb-8">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="eyebrow">Today's attention ledger</h2>
            <button
              onClick={() => navigate("/insights")}
              className="focus-calm group inline-flex items-center gap-1 rounded text-xs font-medium text-primary hover:text-accent"
            >
              Full detail
              <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5" />
            </button>
          </div>

          {ledgerItems.length > 0 ? (
            <AttentionLedger items={ledgerItems} />
          ) : (
            <div className="flex items-center gap-3 rounded-lg border border-signal-clear/30 bg-signal-clear/[0.06] px-5 py-5">
              <CheckCircle2 className="h-5 w-5 shrink-0 text-signal-clear" aria-hidden />
              <p className="text-sm text-foreground">
                No churn, dead stock, or overdue payments are flagged in this dataset.
              </p>
            </div>
          )}
        </section>

        {/* Headline figures — understated inline strip, not hero cards */}
        {headlineFigures.length > 0 && (
          <Reveal className="mb-10 grid grid-cols-1 divide-y divide-border overflow-hidden rounded-lg border border-border bg-card sm:grid-cols-3 sm:divide-x sm:divide-y-0" stagger={0.08}>
            {headlineFigures.map((f) => (
              <RevealItem key={f.label}>
                <div className="px-5 py-4">
                  <p className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">{f.label}</p>
                  <CountUp
                    value={f.value}
                    format={formatINRLakh}
                    className="mt-1 block font-mono text-xl font-semibold tabular-nums text-foreground"
                  />
                  {f.sub && <p className="mt-0.5 text-xs text-muted-foreground">{f.sub}</p>}
                </div>
              </RevealItem>
            ))}
          </Reveal>
        )}

        {/* Executive summary — calm reading block */}
        {summary && (
          <section className="mb-10">
            <h2 className="eyebrow mb-3">Summary</h2>
            <div className="rounded-lg border border-border bg-card p-6">
              <p className="text-[15px] leading-relaxed text-foreground">{summary}</p>
            </div>
          </section>
        )}

        {/* Business signals — a quiet inline row, not a card grid */}
        {signals.length > 0 && (
          <section className="mb-10">
            <h2 className="eyebrow mb-3">Signals</h2>
            <div className="flex flex-wrap gap-x-8 gap-y-3 rounded-lg border border-border bg-card px-5 py-4">
              {signals.map((s) => (
                <div key={s.label}>
                  <p className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">{s.label}</p>
                  <p className="mt-0.5 text-sm font-medium capitalize text-foreground">
                    {String(s.value).replace(/_/g, " ")}
                  </p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Health scores — compact, restrained (no big-number hero template) */}
        {(bi?.revenue_stability_index || bi?.inventory_health_score) && (
          <section className="mb-4">
            <h2 className="eyebrow mb-3">Health</h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {bi?.revenue_stability_index && (
                <ScoreTile
                  label="Revenue stability"
                  score={Math.round(bi.revenue_stability_index.score)}
                  tag={bi.revenue_stability_index.label}
                />
              )}
              {bi?.inventory_health_score && (
                <ScoreTile
                  label="Inventory health"
                  score={Math.round(bi.inventory_health_score.score)}
                  tag={bi.inventory_health_score.label}
                />
              )}
            </div>
          </section>
        )}

        <div className="pt-2">
          <button
            onClick={() => navigate("/insights")}
            className="focus-calm group inline-flex items-center gap-1.5 rounded text-sm font-medium text-primary hover:text-accent"
          >
            See churn, dead stock and receivables in detail
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </button>
        </div>
      </div>
    </AppLayout>
  );
}

function ScoreTile({ label, score, tag }: { label: string; score: number; tag: string }) {
  const tone = score >= 70 ? "text-signal-clear" : score >= 40 ? "text-signal-slowing" : "text-signal-overdue";
  return (
    <div className="flex items-baseline justify-between rounded-lg border border-border bg-card px-5 py-4">
      <div>
        <p className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">{label}</p>
        <p className="mt-1 text-sm font-medium capitalize text-foreground">{tag}</p>
      </div>
      <div className="text-right">
        <span className={cn("font-mono text-2xl font-semibold tabular-nums", tone)}>{score}</span>
        <span className="text-xs text-muted-foreground">/100</span>
      </div>
    </div>
  );
}
