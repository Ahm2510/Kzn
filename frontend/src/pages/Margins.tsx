import { AppLayout } from "@/components/layout/AppLayout";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { PieChart, ArrowUpRight, ArrowDownRight, AlertTriangle } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useLatestCompletedRun } from "@/hooks/useAnalysis";

export default function Margins() {
  const navigate = useNavigate();
  const { data: run, isLoading, error } = useLatestCompletedRun();
  const [searchTerm, setSearchTerm] = useState("");
  const [sortConfig, setSortConfig] = useState<{
    key: string;
    direction: "asc" | "desc";
  } | null>(null);

  if (isLoading) {
    return (
      <AppLayout>
        <div className="page-container animate-fade-in">
          <section className="section-spacing">
            <Skeleton className="h-6 w-48 mb-6" />
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
              <Skeleton className="h-24 rounded-lg" />
              <Skeleton className="h-24 rounded-lg" />
              <Skeleton className="h-24 rounded-lg" />
              <Skeleton className="h-24 rounded-lg" />
            </div>
            <Skeleton className="h-32 w-full rounded-lg mb-8" />
            <Skeleton className="h-96 w-full rounded-lg" />
          </section>
        </div>
      </AppLayout>
    );
  }

  if (error) {
    return (
      <AppLayout>
        <EmptyState
          icon={PieChart}
          title="Unable to load margins"
          description={error.message || "An error occurred while loading margin analysis."}
          action={<Button variant="outline" onClick={() => window.location.reload()}>Try again</Button>}
          className="h-[calc(100vh-3.5rem)]"
        />
      </AppLayout>
    );
  }

  const marginData = run?.insight_report?.business_insights?.margin_analysis;

  if (!marginData) {
    return (
      <AppLayout>
        <EmptyState
          icon={PieChart}
          title="No cost data detected"
          description="To enable margin analysis, include a column named cost_of_goods, cogs, unit_cost, or similar in your dataset."
          action={
            <Button onClick={() => navigate("/datasets")}>
              Upload new dataset
            </Button>
          }
          className="h-[calc(100vh-3.5rem)]"
        />
      </AppLayout>
    );
  }

  const handleSort = (key: string) => {
    let direction: "asc" | "desc" = "desc";
    if (sortConfig && sortConfig.key === key && sortConfig.direction === "desc") {
      direction = "asc";
    }
    setSortConfig({ key, direction });
  };

  const getSortedProducts = () => {
    if (!marginData.product_breakdown || !Array.isArray(marginData.product_breakdown)) {
      return [];
    }
    let sortableItems = [...marginData.product_breakdown];
    if (searchTerm) {
      sortableItems = sortableItems.filter((item) =>
        item.product.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }
    if (sortConfig !== null) {
      sortableItems.sort((a, b) => {
        const aValue = a[sortConfig.key as keyof typeof a];
        const bValue = b[sortConfig.key as keyof typeof b];

        if (typeof aValue === "string" && typeof bValue === "string") {
          return sortConfig.direction === "asc"
            ? aValue.localeCompare(bValue)
            : bValue.localeCompare(aValue);
        } else if (typeof aValue === "number" && typeof bValue === "number") {
          return sortConfig.direction === "asc" ? aValue - bValue : bValue - aValue;
        } else if (typeof aValue === "boolean" && typeof bValue === "boolean") {
          return sortConfig.direction === "asc"
            ? (aValue === bValue ? 0 : aValue ? -1 : 1)
            : (aValue === bValue ? 0 : aValue ? 1 : -1);
        }
        return 0;
      });
    }
    return sortableItems;
  };

  const sortedProducts = getSortedProducts();

  return (
    <AppLayout>
      <div className="page-container animate-fade-in">
        <section className="section-spacing">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-display font-semibold text-foreground tracking-tight">
              Margin Analysis
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="bg-card border border-border rounded-lg p-5 flex flex-col justify-between">
              <p className="text-xs text-muted-foreground mb-2">Overall Margin %</p>
              <div className={`text-3xl font-display font-bold ${
                marginData.overall_margin_pct >= 30 ? "text-emerald-500" :
                marginData.overall_margin_pct >= 15 ? "text-amber-500" :
                "text-red-500"
              }`}>
                {typeof marginData.overall_margin_pct === 'number' ? marginData.overall_margin_pct.toFixed(1) : "—"}%
              </div>
            </div>
            
            <div className="bg-card border border-border rounded-lg p-5 flex flex-col justify-between">
              <p className="text-xs text-muted-foreground mb-2">Gross Profit</p>
              <div className="text-3xl font-display font-bold text-foreground">
                ${typeof marginData.total_gross_profit === 'number' ? marginData.total_gross_profit.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 }) : "—"}
              </div>
            </div>

            <div className={`bg-card border rounded-lg p-5 flex flex-col justify-between ${marginData.products_loss_making > 0 ? 'border-red-500/40 bg-red-500/5' : 'border-border'}`}>
              <p className="text-xs text-muted-foreground mb-2">Loss-Making Products</p>
              <div className="flex items-center gap-2">
                <div className={`text-3xl font-display font-bold ${marginData.products_loss_making > 0 ? "text-red-500" : "text-foreground"}`}>
                  {marginData.products_loss_making}
                </div>
                {marginData.products_loss_making > 0 && (
                  <AlertTriangle className="w-5 h-5 text-red-500" />
                )}
              </div>
            </div>

            {marginData.baseline_margin_pct != null ? (
              <div className="bg-card border border-border rounded-lg p-5 flex flex-col justify-between">
                <p className="text-xs text-muted-foreground mb-2">Margin vs Baseline</p>
                <div className="flex items-center gap-2">
                  <div className="text-3xl font-display font-bold text-foreground">
                    {marginData.margin_change_pct != null ? `${marginData.margin_change_pct >= 0 ? '+' : ''}${marginData.margin_change_pct.toFixed(1)}%` : "—"}
                  </div>
                  {marginData.margin_direction === "improving" && <ArrowUpRight className="w-6 h-6 text-emerald-500" />}
                  {marginData.margin_direction === "declining" && <ArrowDownRight className="w-6 h-6 text-red-500" />}
                </div>
              </div>
            ) : (
              <div className="bg-card border border-border rounded-lg p-5 flex flex-col justify-between opacity-50">
                <p className="text-xs text-muted-foreground mb-2">Margin vs Baseline</p>
                <div className="text-3xl font-display font-bold text-foreground">
                  —
                </div>
              </div>
            )}
          </div>

          <div className={`mb-8 p-6 rounded-lg border ${
            marginData.margin_health === "critical" ? "bg-red-500/5 border-red-500/40 animate-pulse" :
            marginData.margin_health === "thin" ? "bg-amber-500/5 border-amber-500/40" :
            marginData.margin_health === "moderate" ? "bg-blue-500/5 border-blue-500/40" :
            "bg-emerald-500/5 border-emerald-500/40"
          }`}>
            <h3 className={`text-sm font-bold font-mono uppercase mb-2 ${
              marginData.margin_health === "critical" ? "text-red-500" :
              marginData.margin_health === "thin" ? "text-amber-500" :
              marginData.margin_health === "moderate" ? "text-blue-500" :
              "text-emerald-500"
            }`}>
              {marginData.margin_health} Health
            </h3>
            <p className="text-base text-foreground/90">
              {marginData.margin_health_explanation}
            </p>
          </div>

          {marginData.has_product_breakdown && (
            <div className="bg-card border border-border rounded-lg overflow-hidden mb-6">
              <div className="p-4 border-b border-border flex justify-between items-center">
                <h3 className="text-sm font-medium text-foreground">Product Breakdown</h3>
                <input
                  type="text"
                  placeholder="Search products..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="px-3 py-1 text-sm bg-background border border-border rounded-md text-foreground focus:outline-none focus:border-primary"
                />
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm whitespace-nowrap">
                  <thead className="bg-muted/50 text-muted-foreground text-xs font-mono uppercase">
                    <tr>
                      <th className="px-4 py-3 cursor-pointer hover:bg-muted/80" onClick={() => handleSort('product')}>Product</th>
                      <th className="px-4 py-3 cursor-pointer hover:bg-muted/80 text-right" onClick={() => handleSort('revenue')}>Revenue</th>
                      <th className="px-4 py-3 cursor-pointer hover:bg-muted/80 text-right" onClick={() => handleSort('cost')}>Cost</th>
                      <th className="px-4 py-3 cursor-pointer hover:bg-muted/80 text-right" onClick={() => handleSort('gross_profit')}>Gross Profit</th>
                      <th className="px-4 py-3 cursor-pointer hover:bg-muted/80 text-right" onClick={() => handleSort('margin_pct')}>Margin %</th>
                      <th className="px-4 py-3 cursor-pointer hover:bg-muted/80 text-right" onClick={() => handleSort('revenue_share_pct')}>Share %</th>
                      <th className="px-4 py-3 cursor-pointer hover:bg-muted/80 text-center" onClick={() => handleSort('tier')}>Tier</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {sortedProducts.map((p, idx) => (
                      <tr 
                        key={idx} 
                        className={`hover:bg-muted/30 transition-colors ${
                          p.tier === "loss_making" ? "bg-red-500/5" :
                          p.tier === "thin" ? "bg-amber-500/5" : ""
                        }`}
                      >
                        <td className="px-4 py-3 font-medium text-foreground">
                          <div className="flex items-center gap-2">
                            {p.watchlist && <AlertTriangle className="w-3.5 h-3.5 text-amber-500 flex-shrink-0" />}
                            <span className="truncate max-w-[200px]" title={p.product}>{p.product}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right">${typeof p.revenue === 'number' ? p.revenue.toLocaleString() : "—"}</td>
                        <td className="px-4 py-3 text-right">${typeof p.cost === 'number' ? p.cost.toLocaleString() : "—"}</td>
                        <td className="px-4 py-3 text-right">${typeof p.gross_profit === 'number' ? p.gross_profit.toLocaleString() : "—"}</td>
                        <td className={`px-4 py-3 text-right font-mono ${
                          p.margin_pct >= 30 ? "text-emerald-500" :
                          p.margin_pct >= 15 ? "text-amber-500" :
                          "text-red-500"
                        }`}>
                          {typeof p.margin_pct === 'number' ? p.margin_pct.toFixed(1) : "—"}%
                        </td>
                        <td className="px-4 py-3 text-right text-muted-foreground">{typeof p.revenue_share_pct === 'number' ? p.revenue_share_pct.toFixed(1) : "—"}%</td>
                        <td className="px-4 py-3 text-center">
                          <StatusBadge 
                            status={p.tier === "loss_making" ? "error" : p.tier === "thin" ? "warning" : "complete"} 
                            label={p.tier.replace(/_/g, " ")} 
                          />
                        </td>
                      </tr>
                    ))}
                    {sortedProducts.length === 0 && (
                      <tr>
                        <td colSpan={7} className="px-4 py-8 text-center text-muted-foreground">
                          No products found.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div className="text-center">
            <p className="text-xs text-muted-foreground font-mono">
              Margin data sourced from column: <span className="font-bold">{marginData.cost_column_used}</span> · Revenue from: <span className="font-bold">{marginData.revenue_column_used}</span>
            </p>
            {marginData.warning && (
              <p className="text-xs text-amber-500 mt-2 font-medium">
                ⚠ {marginData.warning}
              </p>
            )}
          </div>

        </section>
      </div>
    </AppLayout>
  );
}
