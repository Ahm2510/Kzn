import { useState, useEffect } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { DatasetUploadBox } from "@/components/ui/DatasetUploadBox";
import { ToggleOption } from "@/components/ui/ToggleOption";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/StatusBadge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
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
import { Play, AlertCircle, ChevronDown, ChevronUp, Trash2, Info, CheckCircle2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import {
  useDefaultProject,
  useCreateAnalysis,
  useAnalysisRun,
  useAnalysisRuns,
  useDeleteRun,
} from "@/hooks/useAnalysis";
import { toast } from "sonner";

type MetricSchema = "auto" | "revenue" | "cost" | "quantity" | "custom";

export default function Datasets() {
  const navigate = useNavigate();
  const { data: project } = useDefaultProject();
  const createAnalysis = useCreateAnalysis();
  const { data: allRuns } = useAnalysisRuns();
  const deleteRun = useDeleteRun();

  const [primaryFile, setPrimaryFile] = useState<File | null>(null);
  const [comparisonFile, setComparisonFile] = useState<File | null>(null);
  const [activeRunId, setActiveRunId] = useState<number | null>(null);
  const [showRecent, setShowRecent] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  const [preprocessing, setPreprocessing] = useState({
    dropDuplicates: true,
    dropMissing: true,
    capOutliers: false,
    normalizeColumns: true,
  });

  const [metricSchema, setMetricSchema] = useState<MetricSchema>("auto");
  const [customColumn, setCustomColumn] = useState("");

  // Poll active run
  const { data: activeRun } = useAnalysisRun(activeRunId);

  const isRunning =
    createAnalysis.isPending ||
    activeRun?.status === "pending" ||
    activeRun?.status === "running";

  const canRunAnalysis = primaryFile !== null && !isRunning && !!project;

  const handleRunAnalysis = async () => {
    if (!primaryFile || !project) return;

    const schema = metricSchema === "custom" ? `custom:${customColumn}` : metricSchema;

    try {
      const run = await createAnalysis.mutateAsync({
        projectId: project.id,
        currentFile: primaryFile,
        baselineFile: comparisonFile,
        cleaningOptions: preprocessing,
        metricSchema: schema,
      });
      setActiveRunId(run.id);
      toast.success("Analysis started successfully.");
    } catch (err: unknown) {
      const error = err as Error;
      toast.error(error.message || "Failed to start analysis.");
    }
  };

  // Navigate when run completes
  useEffect(() => {
    if (activeRun?.status === "completed") {
      toast.success("Analysis completed!");
      navigate("/");
    }
  }, [activeRun?.status, navigate]);

  const errorMessage =
    createAnalysis.error?.message ||
    (activeRun?.status === "failed" ? activeRun.error_message : null);

  const formatSize = (bytes: number) => {
    if (bytes >= 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
    if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / 1024).toFixed(1)} KB`;
  };

  const getEstimatedRows = (file: File | null) => {
    if (!file) return 0;
    // Estimate based on size (average CSV row is about 120 bytes)
    return Math.max(1, Math.round(file.size / 120));
  };

  const getFileName = (path: string | null) => {
    if (!path) return "Unknown Dataset";
    return path.split(/[/\\]/).pop() || "Dataset";
  };

  const mapStatus = (status: string): "pending" | "processing" | "complete" | "error" | "idle" => {
    if (status === "pending") return "pending";
    if (status === "running") return "processing";
    if (status === "completed") return "complete";
    if (status === "failed") return "error";
    return "idle";
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteRun.mutateAsync(id);
      toast.success("Analysis run deleted successfully.");
    } catch (err: unknown) {
      const error = err as Error;
      toast.error(error.message || "Failed to delete analysis run.");
    } finally {
      setConfirmDeleteId(null);
    }
  };

  return (
    <AppLayout>
      <div className="page-container animate-fade-in">
        {/* Header Section */}
        <section className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <p className="text-sm font-mono text-muted-foreground uppercase tracking-wider">
              Data Integration
            </p>
            <h2 className="text-3xl font-display font-bold text-foreground mt-1">
              Datasets & Preprocessing
            </h2>
          </div>
          <button
            onClick={() => setShowRecent(!showRecent)}
            className="flex items-center gap-2 px-4 py-2 bg-secondary border border-border rounded-lg text-sm text-foreground hover:bg-secondary/80 hover:border-primary/20 transition-all duration-200"
          >
            Recent Analyses ({allRuns?.length || 0})
            {showRecent ? (
              <ChevronUp className="w-4 h-4 text-muted-foreground" />
            ) : (
              <ChevronDown className="w-4 h-4 text-muted-foreground" />
            )}
          </button>
        </section>

        {/* Recent Analyses Collapsible Panel */}
        {showRecent && (
          <section className="section-spacing animate-fade-in">
            <div className="bg-card border border-border rounded-lg p-5">
              <h3 className="text-sm font-mono text-muted-foreground uppercase tracking-wider mb-4">
                Recent Runs History
              </h3>
              {!allRuns || allRuns.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4 text-center">
                  No previous analysis runs found.
                </p>
              ) : (
                <div className="grid grid-cols-1 gap-3 max-h-96 overflow-y-auto pr-1">
                  {allRuns.map((run) => (
                    <div
                      key={run.id}
                      className="group flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 p-4 border border-border/60 hover:border-primary/20 rounded-lg bg-muted/20 transition-all duration-200"
                    >
                      <div className="space-y-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs font-mono font-semibold text-primary">
                            RUN #{run.id}
                          </span>
                          <StatusBadge status={mapStatus(run.status)} />
                          <span className="text-xs text-muted-foreground">
                            {new Date(run.created_at).toLocaleString()}
                          </span>
                        </div>
                        <p className="text-sm font-medium text-foreground truncate">
                          Primary: <span className="text-muted-foreground font-mono">{getFileName(run.current_file_path)}</span>
                        </p>
                        {run.baseline_file_path && (
                          <p className="text-xs text-muted-foreground truncate">
                            Baseline: <span className="font-mono">{getFileName(run.baseline_file_path)}</span>
                          </p>
                        )}
                      </div>

                      <div className="flex items-center gap-3 shrink-0">
                        <button
                          onClick={() => setConfirmDeleteId(run.id)}
                          className="p-2 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded transition-all duration-200"
                          title="Delete Analysis"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>
        )}

        {/* Upload sections */}
        <section className="section-spacing">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="space-y-2">
              <DatasetUploadBox
                label="Primary dataset"
                description="Upload the primary CSV file for analysis"
                onFileSelect={(file) => setPrimaryFile(file)}
              />
              {primaryFile && (
                <div className="px-4 py-2.5 rounded-lg bg-primary/5 border border-primary/10 text-xs text-muted-foreground flex justify-between items-center animate-fade-in">
                  <span>Size: <strong className="font-mono text-foreground">{formatSize(primaryFile.size)}</strong></span>
                  <span>Estimate: <strong className="font-mono text-foreground">~{getEstimatedRows(primaryFile).toLocaleString()} rows</strong></span>
                </div>
              )}
            </div>

            <div className="space-y-2">
              <DatasetUploadBox
                label="Comparison dataset"
                description="Baseline or previous period data for change detection"
                isOptional
                onFileSelect={(file) => setComparisonFile(file)}
              />
              {comparisonFile && (
                <div className="px-4 py-2.5 rounded-lg bg-primary/5 border border-primary/10 text-xs text-muted-foreground flex justify-between items-center animate-fade-in">
                  <span>Size: <strong className="font-mono text-foreground">{formatSize(comparisonFile.size)}</strong></span>
                  <span>Estimate: <strong className="font-mono text-foreground">~{getEstimatedRows(comparisonFile).toLocaleString()} rows</strong></span>
                </div>
              )}
            </div>
          </div>
        </section>

        {/* Cleaning options */}
        <section className="section-spacing">
          <h3 className="font-display font-semibold text-foreground mb-6">Cleaning options</h3>
          <div className="bg-card border border-border rounded-lg p-6 lg:p-8">
            <div className="space-y-2">
              <ToggleOption
                label="Drop duplicates"
                description="Remove identical rows from dataset"
                checked={preprocessing.dropDuplicates}
                onCheckedChange={(checked) =>
                  setPreprocessing((prev) => ({ ...prev, dropDuplicates: checked }))
                }
                disabled={isRunning}
              />
              <ToggleOption
                label="Drop missing values"
                description="Remove rows with empty cells in critical columns"
                checked={preprocessing.dropMissing}
                onCheckedChange={(checked) =>
                  setPreprocessing((prev) => ({ ...prev, dropMissing: checked }))
                }
                disabled={isRunning}
              />
              <ToggleOption
                label="Cap outliers"
                description="Limit extreme values to 1st and 99th percentile bounds"
                checked={preprocessing.capOutliers}
                onCheckedChange={(checked) =>
                  setPreprocessing((prev) => ({ ...prev, capOutliers: checked }))
                }
                disabled={isRunning}
              />
              <ToggleOption
                label="Normalize column names"
                description="Standardize column names to lowercase and strip special characters"
                checked={preprocessing.normalizeColumns}
                onCheckedChange={(checked) =>
                  setPreprocessing((prev) => ({ ...prev, normalizeColumns: checked }))
                }
                disabled={isRunning}
              />
            </div>
          </div>
        </section>

        {/* Metric Schema selector */}
        <section className="section-spacing">
          <div className="flex items-center gap-2 mb-6">
            <h3 className="font-display font-semibold text-foreground">Metric schema</h3>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button type="button" className="p-1 text-muted-foreground hover:text-foreground transition-colors">
                    <Info className="w-4 h-4" />
                  </button>
                </TooltipTrigger>
                <TooltipContent className="max-w-xs p-3">
                  <p className="text-xs leading-normal">
                    Specify how the primary metric is identified in your dataset. You can let the algorithm auto-detect revenue columns, force specific options, or write a custom column header exactly as it appears in the CSV.
                  </p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
          
          <div className="bg-card border border-border rounded-lg p-6 lg:p-8 space-y-4">
            <select
              value={metricSchema}
              onChange={(e) => setMetricSchema(e.target.value as MetricSchema)}
              disabled={isRunning}
              className="w-full h-10 px-3 rounded-md border border-input bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="auto">Auto (Revenue detection)</option>
              <option value="revenue">Revenue</option>
              <option value="cost">Cost</option>
              <option value="quantity">Quantity</option>
              <option value="custom">Custom column</option>
            </select>
            {metricSchema === "custom" && (
              <Input
                value={customColumn}
                onChange={(e) => setCustomColumn(e.target.value)}
                placeholder="Enter column name exactly (e.g. Sales_Amount)"
                disabled={isRunning}
                className="h-10 animate-fade-in"
              />
            )}
          </div>
        </section>

        {/* Running status */}
        {activeRun && (activeRun.status === "pending" || activeRun.status === "running") && (
          <section className="section-spacing animate-fade-in">
            <div className="bg-primary/5 border border-primary/20 rounded-lg p-6 flex items-center gap-4">
              <div className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
              <div>
                <p className="font-medium text-foreground">Analysis {activeRun.status}</p>
                <p className="text-sm text-muted-foreground mt-1 font-sans">
                  This may take a few moments as we clean your datasets and execute statistical calculations. You will be redirected to the overview page automatically when complete.
                </p>
              </div>
            </div>
          </section>
        )}

        {/* Error */}
        {errorMessage && (
          <section className="section-spacing animate-fade-in">
            <div className="bg-destructive/5 border border-destructive/20 rounded-lg p-6 flex items-start gap-4">
              <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-destructive">Analysis failed</p>
                <p className="text-sm text-muted-foreground mt-1 font-sans">{errorMessage}</p>
              </div>
            </div>
          </section>
        )}

        {/* Run analysis button */}
        <section className="pt-4 flex flex-col gap-2">
          <Button
            size="lg"
            disabled={!canRunAnalysis}
            onClick={handleRunAnalysis}
            className="font-medium h-12 px-8 w-fit bg-primary hover:bg-primary/95 shadow-md shadow-primary/10"
          >
            {isRunning ? (
              <>
                <div className="w-4 h-4 mr-2 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                Running analysis...
              </>
            ) : (
              <>
                <Play className="w-4 h-4 mr-2 fill-current" />
                Run analysis
              </>
            )}
          </Button>
          {!primaryFile && (
            <p className="text-sm text-muted-foreground mt-1">
              Upload a primary dataset to begin analysis
            </p>
          )}
        </section>

        {/* Delete Confirmation Alert Dialog */}
        <AlertDialog open={confirmDeleteId !== null} onOpenChange={(open) => !open && setConfirmDeleteId(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
              <AlertDialogDescription>
                This action cannot be undone. This will permanently delete this analysis run and all related insights, tables, and cached data from the system.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                className="bg-destructive hover:bg-destructive/90 text-destructive-foreground"
                onClick={() => confirmDeleteId && handleDelete(confirmDeleteId)}
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
