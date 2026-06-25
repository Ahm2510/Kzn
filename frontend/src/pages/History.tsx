import { useState, useMemo } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { InsightCard, InsightSeverity } from "@/components/ui/InsightCard";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  History as HistoryIcon,
  ExternalLink,
  Database,
  Trash2,
  Eye,
  SlidersHorizontal,
  ArrowUpDown,
  Clock,
  Settings2,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAnalysisRuns, useDeleteRun } from "@/hooks/useAnalysis";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

type StatusFilter = "all" | "completed" | "processing" | "failed";
type SortField = "created_at-desc" | "created_at-asc" | "id-desc" | "id-asc";

export default function History() {
  const navigate = useNavigate();
  const { data: runs, isLoading, error } = useAnalysisRuns();
  const deleteRun = useDeleteRun();

  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [sortBy, setSortBy] = useState<SortField>("created_at-desc");
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);

  const getFileName = (path: string | null) => {
    if (!path) return "—";
    return path.split(/[/\\]/).pop() || "Dataset";
  };

  const mapStatus = (s: string): "complete" | "error" | "processing" | "pending" | "idle" => {
    if (s === "completed") return "complete";
    if (s === "failed") return "error";
    if (s === "running") return "processing";
    if (s === "pending") return "pending";
    return "idle";
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteRun.mutateAsync(id);
      toast.success("Analysis run deleted successfully.");
      if (selectedRunId === id) {
        setSelectedRunId(null);
      }
    } catch (err: unknown) {
      const error = err as Error;
      toast.error(error.message || "Failed to delete run.");
    } finally {
      setDeleteConfirmId(null);
    }
  };

  // Filter & Sort
  const filteredAndSortedRuns = useMemo(() => {
    if (!runs) return [];
    let result = [...runs];

    // Filter by status
    if (statusFilter !== "all") {
      result = result.filter((run) => {
        if (statusFilter === "completed") return run.status === "completed";
        if (statusFilter === "failed") return run.status === "failed";
        if (statusFilter === "processing") return run.status === "running" || run.status === "pending";
        return true;
      });
    }

    // Sort
    result.sort((a, b) => {
      if (sortBy === "created_at-desc") {
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      }
      if (sortBy === "created_at-asc") {
        return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      }
      if (sortBy === "id-desc") {
        return b.id - a.id;
      }
      if (sortBy === "id-asc") {
        return a.id - b.id;
      }
      return 0;
    });

    return result;
  }, [runs, statusFilter, sortBy]);

  // Selected run details
  const selectedRun = useMemo(() => {
    if (!runs || selectedRunId === null) return null;
    return runs.find((r) => r.id === selectedRunId) || null;
  }, [runs, selectedRunId]);

  if (isLoading) {
    return (
      <AppLayout>
        <div className="page-container animate-fade-in">
          <section className="section-spacing">
            <Skeleton className="h-6 w-48 mb-6" />
            <div className="rounded-lg border border-border overflow-hidden bg-card">
              <div className="p-4 space-y-3">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
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
          icon={HistoryIcon}
          title="Unable to load history"
          description={error.message || "An error occurred while loading analysis history."}
          action={<Button variant="outline" onClick={() => window.location.reload()}>Try again</Button>}
          className="h-[calc(100vh-3.5rem)]"
        />
      </AppLayout>
    );
  }

  if (!runs || runs.length === 0) {
    return (
      <AppLayout>
        <EmptyState
          icon={HistoryIcon}
          title="No past analyses"
          description="Your completed analyses will appear here. Upload a dataset to begin."
          action={
            <Button onClick={() => navigate("/datasets")} className="bg-primary text-primary-foreground hover:bg-primary/95">
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
        {/* Title Block */}
        <section className="mb-6">
          <p className="text-sm font-mono text-muted-foreground uppercase tracking-wider">
            Analysis Archives
          </p>
          <h2 className="text-3xl font-display font-bold text-foreground mt-1">
            Analysis History
          </h2>
        </section>

        {/* Filter Controls Row */}
        <section className="section-spacing">
          <div className="bg-card border border-border rounded-xl p-5 space-y-4">
            <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
              {/* Status tabs */}
              <div className="flex flex-wrap items-center gap-1.5 w-full md:w-auto">
                <button
                  onClick={() => setStatusFilter("all")}
                  className={cn(
                    "text-xs px-3 py-1.5 rounded-lg border transition-all duration-200",
                    statusFilter === "all"
                      ? "bg-primary text-primary-foreground border-primary font-medium"
                      : "bg-muted/30 border-border text-muted-foreground hover:text-foreground hover:bg-muted/50"
                  )}
                >
                  All Runs ({runs.length})
                </button>
                <button
                  onClick={() => setStatusFilter("completed")}
                  className={cn(
                    "text-xs px-3 py-1.5 rounded-lg border transition-all duration-200",
                    statusFilter === "completed"
                      ? "bg-primary text-primary-foreground border-primary font-medium"
                      : "bg-muted/30 border-border text-muted-foreground hover:text-foreground hover:bg-muted/50"
                  )}
                >
                  Completed
                </button>
                <button
                  onClick={() => setStatusFilter("processing")}
                  className={cn(
                    "text-xs px-3 py-1.5 rounded-lg border transition-all duration-200",
                    statusFilter === "processing"
                      ? "bg-primary text-primary-foreground border-primary font-medium"
                      : "bg-muted/30 border-border text-muted-foreground hover:text-foreground hover:bg-muted/50"
                  )}
                >
                  Processing
                </button>
                <button
                  onClick={() => setStatusFilter("failed")}
                  className={cn(
                    "text-xs px-3 py-1.5 rounded-lg border transition-all duration-200",
                    statusFilter === "failed"
                      ? "bg-destructive text-destructive-foreground border-destructive font-medium"
                      : "bg-muted/30 border-border text-muted-foreground hover:text-foreground hover:bg-muted/50"
                  )}
                >
                  Failed
                </button>
              </div>

              {/* Sorting */}
              <div className="flex items-center gap-2 w-full md:w-auto shrink-0 font-sans">
                <ArrowUpDown className="w-3.5 h-3.5 text-muted-foreground" />
                <span className="text-xs text-muted-foreground font-medium">Sort by:</span>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as SortField)}
                  className="h-9 px-3 rounded-md border border-input bg-background text-foreground text-xs focus:outline-none focus:ring-1 focus:ring-ring flex-1 md:flex-initial"
                >
                  <option value="created_at-desc">Created: Newest First</option>
                  <option value="created_at-asc">Created: Oldest First</option>
                  <option value="id-desc">Run ID: High to Low</option>
                  <option value="id-asc">Run ID: Low to High</option>
                </select>
              </div>
            </div>
          </div>
        </section>

        {/* Archives Table */}
        <section className="section-spacing">
          {filteredAndSortedRuns.length === 0 ? (
            <div className="bg-card border border-border rounded-xl p-12 text-center">
              <HistoryIcon className="w-10 h-10 text-muted-foreground/50 mx-auto mb-3" />
              <h4 className="font-semibold text-foreground mb-1">No matching archives</h4>
              <p className="text-sm text-muted-foreground max-w-sm mx-auto">
                No analysis runs matched your active status filter. Choose 'All Runs' to reset.
              </p>
            </div>
          ) : (
            <div className="rounded-xl border border-border overflow-hidden bg-card shadow-sm">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/40 hover:bg-muted/40 border-b border-border/80">
                    <TableHead className="text-xs font-mono font-bold text-muted-foreground py-4 pl-6">ID</TableHead>
                    <TableHead className="text-xs font-mono font-bold text-muted-foreground py-4">Current File</TableHead>
                    <TableHead className="text-xs font-mono font-bold text-muted-foreground py-4">Baseline</TableHead>
                    <TableHead className="text-xs font-mono font-bold text-muted-foreground py-4">Status</TableHead>
                    <TableHead className="text-xs font-mono font-bold text-muted-foreground text-right py-4">Insights</TableHead>
                    <TableHead className="text-xs font-mono font-bold text-muted-foreground py-4 pl-8">Created At</TableHead>
                    <TableHead className="text-xs font-mono font-bold text-muted-foreground w-28 py-4 pr-6" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredAndSortedRuns.map((run) => (
                    <TableRow
                      key={run.id}
                      className="group border-b border-border/60 hover:bg-muted/20 cursor-pointer transition-colors"
                      onClick={() => setSelectedRunId(run.id)}
                    >
                      <TableCell className="font-mono text-sm py-4 pl-6 text-primary font-bold">
                        #{run.id}
                      </TableCell>
                      <TableCell className="font-medium py-4 max-w-[180px] truncate text-foreground">
                        {getFileName(run.current_file_path)}
                      </TableCell>
                      <TableCell className="text-muted-foreground py-4 max-w-[180px] truncate">
                        {getFileName(run.baseline_file_path)}
                      </TableCell>
                      <TableCell className="py-4">
                        <StatusBadge status={mapStatus(run.status)} />
                      </TableCell>
                      <TableCell className="text-right font-mono py-4 text-foreground pr-8">
                        <div className="flex flex-col items-end gap-0.5">
                          <span>{run.insight_report?.insights?.length ?? 0}</span>
                          {run.insight_report?.total_transactions != null && (
                            <span className="text-[10px] text-muted-foreground">
                              {run.insight_report.total_transactions.toLocaleString()} txns
                            </span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-muted-foreground text-xs py-4 pl-8 font-sans">
                        {new Date(run.created_at).toLocaleString("en-US", {
                          month: "short",
                          day: "numeric",
                          year: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </TableCell>
                      <TableCell className="py-4 pr-6" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center gap-1 justify-end">
                          <button
                            onClick={() => setSelectedRunId(run.id)}
                            className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors"
                            title="View Details"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>
                          {run.status === "completed" && (
                            <button
                              onClick={() => navigate(`/report?id=${run.id}`)}
                              className="p-1.5 text-muted-foreground hover:text-primary hover:bg-primary/10 rounded transition-colors"
                              title="Open Executive Report"
                            >
                              <ExternalLink className="w-3.5 h-3.5" />
                            </button>
                          )}
                          <button
                            onClick={() => setDeleteConfirmId(run.id)}
                            className="p-1.5 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded transition-colors"
                            title="Delete Analysis"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          <p className="text-xs text-muted-foreground mt-6 font-sans">
            Analysis logs and data points are stored in secure archives. Retained for 90 days. Contact your systems administrator for policy adjustments.
          </p>
        </section>

        {/* Detailed Side-Drawer (Sheet) */}
        <Sheet open={selectedRun !== null} onOpenChange={(open) => !open && setSelectedRunId(null)}>
          <SheetContent className="w-full sm:w-[520px] sm:max-w-none overflow-y-auto space-y-6">
            {selectedRun && (
              <>
                <SheetHeader>
                  <span className="text-[10px] font-mono text-primary uppercase font-bold tracking-wider">Analysis Pipeline Metadatas</span>
                  <SheetTitle className="text-xl font-display font-bold">Run #{selectedRun.id} Details</SheetTitle>
                  <SheetDescription className="font-sans">
                    Archived details and configurations executed on this dataset run.
                  </SheetDescription>
                </SheetHeader>

                <div className="space-y-4">
                  {/* Status Badge */}
                  <div className="flex justify-between items-center py-2.5 border-b border-border/50">
                    <span className="text-xs text-muted-foreground">Pipeline Status:</span>
                    <StatusBadge status={mapStatus(selectedRun.status)} />
                  </div>

                  {/* Created Time */}
                  <div className="flex justify-between items-center py-2.5 border-b border-border/50">
                    <span className="text-xs text-muted-foreground flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" /> Date:
                    </span>
                    <span className="text-xs text-foreground font-mono">
                      {new Date(selectedRun.created_at).toLocaleString()}
                    </span>
                  </div>

                  {/* Primary File name */}
                  <div className="py-2.5 border-b border-border/50 space-y-1">
                    <span className="text-xs text-muted-foreground block">Primary Dataset:</span>
                    <span className="text-xs text-foreground font-mono block truncate bg-muted/30 p-2 rounded border">
                      {getFileName(selectedRun.current_file_path)}
                    </span>
                  </div>

                  {/* Baseline File name */}
                  {selectedRun.baseline_file_path && (
                    <div className="py-2.5 border-b border-border/50 space-y-1">
                      <span className="text-xs text-muted-foreground block">Baseline Period:</span>
                      <span className="text-xs text-foreground font-mono block truncate bg-muted/30 p-2 rounded border">
                        {getFileName(selectedRun.baseline_file_path)}
                      </span>
                    </div>
                  )}

                  {/* Preprocessing choices */}
                  <div className="py-3 space-y-2">
                    <span className="text-xs text-muted-foreground flex items-center gap-1.5 font-bold uppercase font-mono tracking-wider">
                      <Settings2 className="w-3.5 h-3.5 text-primary" /> Preprocessing Applied:
                    </span>
                    <div className="bg-muted/20 border border-border p-3.5 rounded-lg space-y-2 text-xs font-sans">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Drop Duplicates:</span>
                        <span className="font-semibold text-foreground">
                          {selectedRun.cleaning_options?.dropDuplicates ? "Enabled" : "Disabled"}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Drop Missing Cells:</span>
                        <span className="font-semibold text-foreground">
                          {selectedRun.cleaning_options?.dropMissing ? "Enabled" : "Disabled"}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Cap percentile outliers:</span>
                        <span className="font-semibold text-foreground">
                          {selectedRun.cleaning_options?.capOutliers ? "Enabled" : "Disabled"}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Normalize columns syntax:</span>
                        <span className="font-semibold text-foreground">
                          {selectedRun.cleaning_options?.normalizeColumns ? "Enabled" : "Disabled"}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Actions buttons */}
                  <div className="pt-4 flex flex-col gap-2">
                    {selectedRun.status === "completed" ? (
                      <Button
                        className="w-full bg-primary text-primary-foreground hover:bg-primary/95"
                        onClick={() => {
                          setSelectedRunId(null);
                          navigate(`/report?id=${selectedRun.id}`);
                        }}
                      >
                        <ExternalLink className="w-4 h-4 mr-2" /> Open Report Dashboard
                      </Button>
                    ) : selectedRun.status === "failed" && selectedRun.error_message ? (
                      <div className="p-3.5 bg-destructive/5 border border-destructive/15 text-destructive rounded-lg space-y-1 text-xs">
                        <span className="font-bold block">Analysis Error Log:</span>
                        <p>{selectedRun.error_message}</p>
                      </div>
                    ) : (
                      <div className="p-3.5 bg-primary/5 border border-primary/10 text-primary rounded-lg text-xs text-center animate-pulse">
                        Dataset is currently compiling inside views engines...
                      </div>
                    )}
                    
                    <Button
                      variant="outline"
                      className="w-full text-destructive hover:bg-destructive/10 hover:text-destructive border-border/50"
                      onClick={() => setDeleteConfirmId(selectedRun.id)}
                    >
                      <Trash2 className="w-4 h-4 mr-2" /> Delete Archive
                    </Button>
                  </div>

                  {/* Quick Insights Preview */}
                  {selectedRun.insight_report?.business_insights?.executive_takeaways && selectedRun.insight_report.business_insights.executive_takeaways.length > 0 && (
                    <div className="pt-4 border-t border-border/50 space-y-3">
                      <span className="text-xs text-muted-foreground block font-bold uppercase tracking-wider font-mono">
                        Executive Takeaways
                      </span>
                      <ul className="space-y-2 pl-1">
                        {selectedRun.insight_report.business_insights.executive_takeaways.slice(0, 3).map((t: string, idx: number) => (
                          <li key={idx} className="text-xs text-foreground flex items-start gap-2">
                            <span className="w-4 h-4 rounded-full bg-primary/10 text-primary flex items-center justify-center font-mono font-bold text-[9px] shrink-0 mt-0.5">
                              {idx + 1}
                            </span>
                            <p className="leading-relaxed">{t}</p>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {selectedRun.insight_report?.insights && selectedRun.insight_report.insights.length > 0 && (
                    <div className="pt-4 border-t border-border/50 space-y-3">
                      <span className="text-xs text-muted-foreground flex items-center justify-between font-bold uppercase tracking-wider font-mono">
                        <span>Top Insights</span>
                        <span className="font-sans text-[10px] font-normal lowercase opacity-80 flex gap-2">
                          <span>{selectedRun.insight_report?.insights?.length ?? 0} insights</span>
                          {selectedRun.insight_report?.total_transactions != null && (
                            <span>&middot; {selectedRun.insight_report.total_transactions.toLocaleString()} transactions</span>
                          )}
                          {selectedRun.baseline_file_path && (
                            <span>&middot; Comparison included</span>
                          )}
                        </span>
                      </span>
                      <div className="space-y-3">
                        {selectedRun.insight_report.insights.slice(0, 3).map((insight: { title: string; description: string; severity?: string; confidence?: string }, idx: number) => (
                          <InsightCard
                            key={idx}
                            title={insight.title}
                            description={insight.description}
                            severity={(insight.severity as InsightSeverity) || "low"}
                            confidence={insight.confidence}
                            expandable={false}
                            className="bg-card/50 shadow-none border-border/50"
                          />
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </>
            )}
          </SheetContent>
        </Sheet>

        {/* Delete Confirmation Alert Dialog */}
        <AlertDialog open={deleteConfirmId !== null} onOpenChange={(open) => !open && setDeleteConfirmId(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
              <AlertDialogDescription>
                This action cannot be undone. This will permanently delete this analysis run and all related insights, tables, and cached data from the system databases.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                className="bg-destructive hover:bg-destructive/90 text-destructive-foreground"
                onClick={() => deleteConfirmId && handleDelete(deleteConfirmId)}
              >
                Delete Run
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </AppLayout>
  );
}
