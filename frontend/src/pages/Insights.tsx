import { useState, useMemo } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { InsightCard, InsightSeverity } from "@/components/ui/InsightCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Lightbulb, Database, Search, ArrowUpDown } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useLatestCompletedRun } from "@/hooks/useAnalysis";
import { cn } from "@/lib/utils";

type SeverityFilter = "all" | "high" | "medium" | "low";
type SortOption = "default" | "severity-desc" | "confidence-desc" | "alphabetical";

export default function Insights() {
  const navigate = useNavigate();
  const { data: run, isLoading, error } = useLatestCompletedRun();

  const [searchTerm, setSearchTerm] = useState("");
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("all");
  const [sortBy, setSortBy] = useState<SortOption>("default");

  const insights = useMemo(() => {
    return run?.insight_report?.insights || [];
  }, [run]);

  // Compute counts
  const counts = useMemo(() => {
    const res = { all: insights.length, high: 0, medium: 0, low: 0 };
    insights.forEach((ins) => {
      if (ins.severity === "high") res.high++;
      else if (ins.severity === "medium") res.medium++;
      else if (ins.severity === "low") res.low++;
    });
    return res;
  }, [insights]);

  // Filter & Sort
  const filteredAndSortedInsights = useMemo(() => {
    let result = [...insights];

    // Filter by search
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      result = result.filter(
        (ins) =>
          ins.title.toLowerCase().includes(q) ||
          ins.description.toLowerCase().includes(q) ||
          (ins.driver && ins.driver.toLowerCase().includes(q)) ||
          (ins.implication && ins.implication.toLowerCase().includes(q)) ||
          (ins.action_direction && ins.action_direction.toLowerCase().includes(q))
      );
    }

    // Filter by severity
    if (severityFilter !== "all") {
      result = result.filter((ins) => ins.severity === severityFilter);
    }

    // Sort
    if (sortBy === "severity-desc") {
      const severityWeight = { high: 3, medium: 2, low: 1 };
      result.sort((a, b) => (severityWeight[b.severity] || 0) - (severityWeight[a.severity] || 0));
    } else if (sortBy === "confidence-desc") {
      const confidenceWeight = (conf?: string) => {
        if (!conf) return 0;
        const c = conf.toUpperCase();
        if (c === "HIGH") return 3;
        if (c === "MEDIUM") return 2;
        if (c === "LOW") return 1;
        return 0;
      };
      result.sort((a, b) => confidenceWeight(b.confidence) - confidenceWeight(a.confidence));
    } else if (sortBy === "alphabetical") {
      result.sort((a, b) => a.title.localeCompare(b.title));
    }

    return result;
  }, [insights, searchTerm, severityFilter, sortBy]);

  const handleClearFilters = () => {
    setSearchTerm("");
    setSeverityFilter("all");
    setSortBy("default");
  };

  if (isLoading) {
    return (
      <AppLayout>
        <div className="page-container animate-fade-in">
          <section className="section-spacing">
            <Skeleton className="h-6 w-48 mb-6" />
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

  if (insights.length === 0) {
    return (
      <AppLayout>
        <EmptyState
          icon={Lightbulb}
          title="No insights generated"
          description="Upload and analyze a dataset to generate deep automated insights."
          action={
            <Button onClick={() => navigate("/datasets")} className="bg-primary hover:bg-primary/95 text-primary-foreground">
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
        {/* Header Block */}
        <section className="mb-8">
          <p className="text-sm font-mono text-muted-foreground uppercase tracking-wider">
            Automated Intelligence
          </p>
          <h2 className="text-3xl font-display font-bold text-foreground mt-1">
            Data Insights & Signals
          </h2>
          <p className="text-sm text-muted-foreground mt-2 max-w-2xl font-sans">
            Here are the structural findings, outliers, and optimization recommendations computed from your latest dataset analysis.
          </p>
        </section>

        {/* Dynamic Summary Cards */}
        <section className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="p-4 rounded-xl bg-card border border-border/80 text-center space-y-1">
            <span className="text-2xl font-display font-bold text-foreground">{counts.all}</span>
            <p className="text-xs text-muted-foreground uppercase font-mono tracking-wider">Total Findings</p>
          </div>
          <div className="p-4 rounded-xl bg-destructive/5 border border-destructive/20 text-center space-y-1">
            <span className="text-2xl font-display font-bold text-destructive">{counts.high}</span>
            <p className="text-xs text-destructive/80 uppercase font-mono tracking-wider">High Severity</p>
          </div>
          <div className="p-4 rounded-xl bg-gold/5 border border-gold/20 text-center space-y-1">
            <span className="text-2xl font-display font-bold text-gold">{counts.medium}</span>
            <p className="text-xs text-gold/80 uppercase font-mono tracking-wider">Medium Severity</p>
          </div>
          <div className="p-4 rounded-xl bg-primary/5 border border-primary/20 text-center space-y-1">
            <span className="text-2xl font-display font-bold text-primary">{counts.low}</span>
            <p className="text-xs text-primary/85 uppercase font-mono tracking-wider">Low Severity</p>
          </div>
        </section>

        {/* Filter Controls Row */}
        <section className="section-spacing">
          <div className="bg-card border border-border rounded-xl p-5 space-y-4">
            <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
              {/* Search */}
              <div className="relative w-full md:w-80">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Search insights..."
                  className="pl-9 bg-muted/20 border-border"
                />
              </div>

              {/* Sort selector */}
              <div className="flex items-center gap-2 w-full md:w-auto shrink-0">
                <ArrowUpDown className="w-4 h-4 text-muted-foreground" />
                <span className="text-xs text-muted-foreground shrink-0 font-medium">Sort by:</span>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as SortOption)}
                  className="h-9 px-3 rounded-md border border-input bg-background text-foreground text-xs focus:outline-none focus:ring-1 focus:ring-ring flex-1 md:flex-initial"
                >
                  <option value="default">Default Order</option>
                  <option value="severity-desc">Severity: High to Low</option>
                  <option value="confidence-desc">Confidence: High to Low</option>
                  <option value="alphabetical">Alphabetical</option>
                </select>
              </div>
            </div>

            {/* Severity Filter buttons row */}
            <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-border/50">
              <div className="flex flex-wrap items-center gap-2">
                <button
                  onClick={() => setSeverityFilter("all")}
                  className={cn(
                    "text-xs px-3 py-1.5 rounded-lg border transition-all duration-200",
                    severityFilter === "all"
                      ? "bg-primary text-primary-foreground border-primary font-medium shadow-sm"
                      : "bg-muted/30 border-border/80 text-muted-foreground hover:text-foreground hover:bg-muted/50"
                  )}
                >
                  All ({counts.all})
                </button>
                <button
                  onClick={() => setSeverityFilter("high")}
                  className={cn(
                    "text-xs px-3 py-1.5 rounded-lg border transition-all duration-200",
                    severityFilter === "high"
                      ? "bg-destructive text-destructive-foreground border-destructive font-medium shadow-sm"
                      : "bg-destructive/5 border-destructive/15 text-destructive/80 hover:bg-destructive/10"
                  )}
                >
                  High ({counts.high})
                </button>
                <button
                  onClick={() => setSeverityFilter("medium")}
                  className={cn(
                    "text-xs px-3 py-1.5 rounded-lg border transition-all duration-200",
                    severityFilter === "medium"
                      ? "bg-gold text-gold-foreground border-gold font-medium shadow-sm"
                      : "bg-gold/5 border-gold/15 text-gold/80 hover:bg-gold/10"
                  )}
                >
                  Medium ({counts.medium})
                </button>
                <button
                  onClick={() => setSeverityFilter("low")}
                  className={cn(
                    "text-xs px-3 py-1.5 rounded-lg border transition-all duration-200",
                    severityFilter === "low"
                      ? "bg-primary text-primary-foreground border-primary font-medium shadow-sm"
                      : "bg-primary/5 border-primary/15 text-primary/80 hover:bg-primary/10"
                  )}
                >
                  Low ({counts.low})
                </button>
              </div>

              {(searchTerm || severityFilter !== "all" || sortBy !== "default") && (
                <button
                  onClick={handleClearFilters}
                  className="text-xs text-primary font-medium hover:underline focus:outline-none"
                >
                  Reset all filters
                </button>
              )}
            </div>
          </div>
        </section>

        {/* Insights list */}
        <section className="section-spacing">
          {filteredAndSortedInsights.length === 0 ? (
            <div className="bg-card border border-border/80 rounded-xl p-12 text-center">
              <Lightbulb className="w-10 h-10 text-muted-foreground/60 mx-auto mb-4" />
              <h4 className="font-semibold text-foreground mb-1">No matching insights</h4>
              <p className="text-sm text-muted-foreground max-w-sm mx-auto mb-4">
                No findings match your current search queries or filter selections. Try resetting your search terms.
              </p>
              <Button onClick={handleClearFilters} variant="outline" size="sm">
                Clear Filters
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredAndSortedInsights.map((insight, idx) => (
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
                  expandable={true}
                  defaultExpanded={insight.severity === "high"}
                />
              ))}
            </div>
          )}
        </section>
      </div>
    </AppLayout>
  );
}
