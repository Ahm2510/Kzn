import { useEffect, useMemo, useState } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { History as HistoryIcon, ExternalLink, Database } from "lucide-react";
import { useNavigate } from "react-router-dom";

import * as serviceA from "@/api/serviceA";

// Types for backend data
interface HistoryEntry {
  id: number;
  primaryDataset: string;
  comparisonDataset: string | null;
  status: "complete" | "error" | "processing";
  insightCount: number;
  timestamp: string;
}

// State type
type HistoryState = 
  | { status: "loading" }
  | { status: "empty" }
  | { status: "error"; message: string }
  | { status: "success"; data: HistoryEntry[] };

export default function History() {
  const navigate = useNavigate();

  const [state, setState] = useState<HistoryState>({ status: "loading" });

  const toHistoryEntry = useMemo(() => {
    return (run: serviceA.AnalysisRun): HistoryEntry => {
      const report = run.insight_report as any;
      const insightCount = Array.isArray(report?.insights) ? report.insights.length : 0;
      const status: HistoryEntry["status"] =
        run.status === "completed" ? "complete" : run.status === "failed" ? "error" : "processing";
      return {
        id: run.id,
        primaryDataset: run.current_file_path,
        comparisonDataset: run.baseline_file_path,
        status,
        insightCount,
        timestamp: new Date(run.created_at).toLocaleString(),
      };
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setState({ status: "loading" });
      try {
        const runs = await serviceA.listAnalysisRuns();
        if (cancelled) return;
        if (!runs.length) {
          setState({ status: "empty" });
          return;
        }
        setState({ status: "success", data: runs.map(toHistoryEntry) });
      } catch (e) {
        if (cancelled) return;
        const err = e as { status?: number };
        if (err?.status === 403) {
          setState({ status: "error", message: "Not authenticated. Please login again." });
        } else {
          setState({ status: "error", message: "Unable to load history." });
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [toHistoryEntry]);

  // Loading state
  if (state.status === "loading") {
    return (
      <AppLayout>
        <div className="page-container animate-fade-in">
          <section>
            <div className="mb-8">
              <Skeleton className="h-4 w-40" />
            </div>
            <div className="rounded-lg border border-border overflow-hidden">
              <div className="p-4 space-y-3">
                <Skeleton className="h-16 w-full" />
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

  // Error state
  if (state.status === "error") {
    return (
      <AppLayout>
        <EmptyState
          icon={HistoryIcon}
          title="Unable to load history"
          description={state.message || "An error occurred while loading analysis history."}
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

  // Empty state
  if (state.status === "empty") {
    return (
      <AppLayout>
        <EmptyState
          icon={HistoryIcon}
          title="No past analyses"
          description="Your completed analyses will appear here. Upload a dataset to begin."
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

  // Success state
  const historyEntries = state.data;

  return (
    <AppLayout>
      <div className="page-container animate-fade-in">
        <section>
          <div className="mb-8">
            <p className="text-sm text-muted-foreground font-mono">
              {historyEntries.length} analysis{historyEntries.length !== 1 ? "es" : ""} completed
            </p>
          </div>

          <div className="rounded-lg border border-border overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="bg-card hover:bg-card">
                  <TableHead className="text-xs font-mono font-medium text-muted-foreground py-4">
                    Primary Dataset
                  </TableHead>
                  <TableHead className="text-xs font-mono font-medium text-muted-foreground py-4">
                    Comparison
                  </TableHead>
                  <TableHead className="text-xs font-mono font-medium text-muted-foreground py-4">
                    Status
                  </TableHead>
                  <TableHead className="text-xs font-mono font-medium text-muted-foreground text-right py-4">
                    Insights
                  </TableHead>
                  <TableHead className="text-xs font-mono font-medium text-muted-foreground py-4">
                    Timestamp
                  </TableHead>
                  <TableHead className="text-xs font-mono font-medium text-muted-foreground w-16 py-4">
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {historyEntries.map((entry) => (
                  <TableRow key={entry.id} className="group">
                    <TableCell className="font-medium py-6">
                      {entry.primaryDataset}
                    </TableCell>
                    <TableCell className="text-muted-foreground py-6">
                      {entry.comparisonDataset || "—"}
                    </TableCell>
                    <TableCell className="py-6">
                      <StatusBadge status={entry.status} />
                    </TableCell>
                    <TableCell className="text-right font-mono py-6">
                      {entry.insightCount}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm py-6">
                      {entry.timestamp}
                    </TableCell>
                    <TableCell className="py-6">
                      {entry.status === "complete" && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-9 w-9 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                          onClick={() => navigate(`/report?id=${entry.id}`)}
                        >
                          <ExternalLink className="w-4 h-4" />
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <p className="text-xs text-muted-foreground mt-6">
            Analysis history is retained for 90 days. Contact support for extended retention.
          </p>
        </section>
      </div>
    </AppLayout>
  );
}
