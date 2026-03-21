import { useState, useEffect } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { DatasetUploadBox } from "@/components/ui/DatasetUploadBox";
import { ToggleOption } from "@/components/ui/ToggleOption";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Play, AlertCircle, CheckCircle2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useDefaultProject, useCreateAnalysis, useAnalysisRun } from "@/hooks/useAnalysis";

type MetricSchema = "auto" | "revenue" | "cost" | "quantity" | "custom";

export default function Datasets() {
  const navigate = useNavigate();
  const { data: project } = useDefaultProject();
  const createAnalysis = useCreateAnalysis();

  const [primaryFile, setPrimaryFile] = useState<File | null>(null);
  const [comparisonFile, setComparisonFile] = useState<File | null>(null);
  const [activeRunId, setActiveRunId] = useState<number | null>(null);

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

  const isRunning = createAnalysis.isPending || activeRun?.status === "pending" || activeRun?.status === "running";
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
    } catch {
      // error is captured by mutation state
    }
  };

  // Navigate when run completes
  useEffect(() => {
    if (activeRun?.status === "completed") {
      navigate("/");
    }
  }, [activeRun?.status, navigate]);

  const errorMessage =
    createAnalysis.error?.message ||
    (activeRun?.status === "failed" ? activeRun.error_message : null);

  return (
    <AppLayout>
      <div className="page-container animate-fade-in">
        {/* Upload sections */}
        <section className="section-spacing">
          <div className="space-y-8">
            <DatasetUploadBox
              label="Primary dataset"
              description="Upload the primary CSV file for analysis"
              onFileSelect={(file) => setPrimaryFile(file)}
            />
            <DatasetUploadBox
              label="Comparison dataset"
              description="Baseline or previous period data for change detection"
              isOptional
              onFileSelect={(file) => setComparisonFile(file)}
            />
          </div>
        </section>

        {/* Cleaning options */}
        <section className="section-spacing">
          <h3 className="font-display font-semibold text-foreground mb-6">Cleaning options</h3>
          <div className="bg-card border border-border rounded-lg p-6 lg:p-8">
            <div className="space-y-2">
              <ToggleOption label="Drop duplicates" description="Remove identical rows from dataset" checked={preprocessing.dropDuplicates} onCheckedChange={(checked) => setPreprocessing((prev) => ({ ...prev, dropDuplicates: checked }))} disabled={isRunning} />
              <ToggleOption label="Drop missing values" description="Remove rows with empty cells" checked={preprocessing.dropMissing} onCheckedChange={(checked) => setPreprocessing((prev) => ({ ...prev, dropMissing: checked }))} disabled={isRunning} />
              <ToggleOption label="Cap outliers" description="Limit extreme values to percentile bounds" checked={preprocessing.capOutliers} onCheckedChange={(checked) => setPreprocessing((prev) => ({ ...prev, capOutliers: checked }))} disabled={isRunning} />
              <ToggleOption label="Normalize column names" description="Standardize column names and formats" checked={preprocessing.normalizeColumns} onCheckedChange={(checked) => setPreprocessing((prev) => ({ ...prev, normalizeColumns: checked }))} disabled={isRunning} />
            </div>
          </div>
        </section>

        {/* Metric Schema selector */}
        <section className="section-spacing">
          <h3 className="font-display font-semibold text-foreground mb-6">Metric schema</h3>
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
              <Input value={customColumn} onChange={(e) => setCustomColumn(e.target.value)} placeholder="Enter column name" disabled={isRunning} className="h-10" />
            )}
          </div>
        </section>

        {/* Running status */}
        {activeRun && (activeRun.status === "pending" || activeRun.status === "running") && (
          <section className="animate-fade-in">
            <div className="bg-primary/5 border border-primary/20 rounded-lg p-6 flex items-center gap-4">
              <div className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
              <div>
                <p className="font-medium text-foreground">Analysis {activeRun.status}</p>
                <p className="text-sm text-muted-foreground mt-1">This may take a few moments. You'll be redirected when complete.</p>
              </div>
            </div>
          </section>
        )}

        {/* Error */}
        {errorMessage && (
          <section className="animate-fade-in">
            <div className="bg-destructive/5 border border-destructive/20 rounded-lg p-6 flex items-start gap-4">
              <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-destructive">Analysis failed</p>
                <p className="text-sm text-muted-foreground mt-1">{errorMessage}</p>
              </div>
            </div>
          </section>
        )}

        {/* Run analysis button */}
        <section className="pt-4">
          <Button size="lg" disabled={!canRunAnalysis} onClick={handleRunAnalysis} className="font-medium h-12 px-8">
            {isRunning ? (
              <>
                <div className="w-4 h-4 mr-2 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                Running analysis...
              </>
            ) : (
              <>
                <Play className="w-4 h-4 mr-2" />
                Run analysis
              </>
            )}
          </Button>
          {!primaryFile && (
            <p className="text-sm text-muted-foreground mt-4">Upload a primary dataset to begin analysis</p>
          )}
        </section>
      </div>
    </AppLayout>
  );
}
