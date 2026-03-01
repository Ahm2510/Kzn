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
import { useAnalysisRuns } from "@/hooks/useAnalysis";

function mapStatus(s: string): "complete" | "error" | "processing" {
  if (s === "completed") return "complete";
  if (s === "failed") return "error";
  return "processing";
}

export default function History() {
  const navigate = useNavigate();
  const { data: runs, isLoading, error } = useAnalysisRuns();

  if (isLoading) {
    return (
      <AppLayout>
        <div className="page-container animate-fade-in">
          <section>
            <div className="mb-8"><Skeleton className="h-4 w-40" /></div>
            <div className="rounded-lg border border-border overflow-hidden">
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

  return (
    <AppLayout>
      <div className="page-container animate-fade-in">
        <section>
          <div className="mb-8">
            <p className="text-sm text-muted-foreground font-mono">
              {runs.length} analysis{runs.length !== 1 ? "es" : ""} found
            </p>
          </div>

          <div className="rounded-lg border border-border overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="bg-card hover:bg-card">
                  <TableHead className="text-xs font-mono font-medium text-muted-foreground py-4">ID</TableHead>
                  <TableHead className="text-xs font-mono font-medium text-muted-foreground py-4">Current File</TableHead>
                  <TableHead className="text-xs font-mono font-medium text-muted-foreground py-4">Baseline</TableHead>
                  <TableHead className="text-xs font-mono font-medium text-muted-foreground py-4">Status</TableHead>
                  <TableHead className="text-xs font-mono font-medium text-muted-foreground text-right py-4">Insights</TableHead>
                  <TableHead className="text-xs font-mono font-medium text-muted-foreground py-4">Created</TableHead>
                  <TableHead className="text-xs font-mono font-medium text-muted-foreground w-16 py-4" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {runs.map((run) => (
                  <TableRow key={run.id} className="group">
                    <TableCell className="font-mono text-sm py-6">#{run.id}</TableCell>
                    <TableCell className="font-medium py-6">{run.current_file_path?.split("/").pop() || "—"}</TableCell>
                    <TableCell className="text-muted-foreground py-6">{run.baseline_file_path?.split("/").pop() || "—"}</TableCell>
                    <TableCell className="py-6"><StatusBadge status={mapStatus(run.status)} /></TableCell>
                    <TableCell className="text-right font-mono py-6">{run.insight_report?.insights?.length ?? "—"}</TableCell>
                    <TableCell className="text-muted-foreground text-sm py-6">
                      {new Date(run.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="py-6">
                      {run.status === "completed" && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-9 w-9 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                          onClick={() => navigate(`/report?id=${run.id}`)}
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
