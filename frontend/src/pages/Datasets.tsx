import { useEffect, useMemo, useState } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { DatasetUploadBox } from "@/components/ui/DatasetUploadBox";
import { ToggleOption } from "@/components/ui/ToggleOption";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Play, AlertCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";

import * as serviceA from "@/api/serviceA";

// Checklist §4: Metric Schema options
type MetricSchema = "auto" | "revenue" | "cost" | "quantity" | "custom";

// State types
type SchemaState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success" };

type AnalysisState =
  | { status: "idle" }
  | { status: "running" }
  | { status: "error"; message: string };

export default function Datasets() {
  const navigate = useNavigate();
  const [primaryFile, setPrimaryFile] = useState<File | null>(null);
  const [comparisonFile, setComparisonFile] = useState<File | null>(null);

  // Checklist §4: Cleaning options — exactly these four
  const [preprocessing, setPreprocessing] = useState({
    dropDuplicates: true,
    dropMissing: true,
    capOutliers: false,
    normalizeColumns: true,
  });

  // Checklist §4: Metric Schema selector
  const [metricSchema, setMetricSchema] = useState<MetricSchema>("auto");
  const [customColumn, setCustomColumn] = useState("");

  const [schemaState] = useState<SchemaState>({ status: "idle" });
  const [analysisState, setAnalysisState] = useState<AnalysisState>({ status: "idle" });

  const [projects, setProjects] = useState<serviceA.Project[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [projectError, setProjectError] = useState<string | null>(null);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [newProjectName, setNewProjectName] = useState("My Project");

  const canRunAnalysis = primaryFile !== null && analysisState.status !== "running";

  const metricSchemaParam = useMemo(() => {
    if (metricSchema === "custom") {
      const col = customColumn.trim();
      return col ? `custom:${col}` : null;
    }
    return metricSchema;
  }, [metricSchema, customColumn]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setProjectsLoading(true);
      setProjectError(null);
      try {
        const data = await serviceA.listProjects();
        if (cancelled) return;
        setProjects(data);
        if (data.length > 0 && selectedProjectId == null) {
          setSelectedProjectId(data[0].id);
        }
      } catch (e) {
        if (cancelled) return;
        const err = e as { status?: number };
        if (err?.status === 403) {
          setProjectError("Not authenticated. Please login again.");
        } else {
          setProjectError("Unable to load projects.");
        }
      } finally {
        if (!cancelled) setProjectsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedProjectId]);

  const handlePrimaryFileSelect = (file: File) => {
    setPrimaryFile(file);
  };

  const handleCreateProject = async () => {
    const name = newProjectName.trim();
    if (!name) return;
    setProjectError(null);
    try {
      const created = await serviceA.createProject(name);
      setProjects((prev) => [created, ...prev]);
      setSelectedProjectId(created.id);
    } catch (e) {
      const err = e as { status?: number; bodyText?: string };
      if (err?.status === 400) {
        setProjectError("Invalid project name.");
      } else if (err?.status === 403) {
        setProjectError("Not authenticated. Please login again.");
      } else {
        setProjectError("Failed to create project.");
      }
    }
  };

  const handleRunAnalysis = async () => {
    if (!primaryFile) return;
    if (!selectedProjectId) {
      setAnalysisState({ status: "error", message: "Select or create a project first." });
      return;
    }

    setAnalysisState({ status: "running" });

    try {
      const run = await serviceA.startAnalysis({
        projectId: selectedProjectId,
        currentFile: primaryFile,
        baselineFile: comparisonFile,
        cleaningOptions: {
          dropDuplicates: preprocessing.dropDuplicates,
          dropMissing: preprocessing.dropMissing,
          capOutliers: preprocessing.capOutliers,
          normalizeColumns: preprocessing.normalizeColumns,
        },
        metricSchema: metricSchemaParam,
      });

      navigate(`/insights?id=${run.id}`);
    } catch (e) {
      const err = e as { status?: number; bodyText?: string };
      if (err?.status === 403) {
        setAnalysisState({ status: "error", message: "Not authenticated. Please login again." });
      } else if (err?.status === 400) {
        setAnalysisState({ status: "error", message: "Validation error. Check inputs and try again." });
      } else if (err?.status === 404) {
        setAnalysisState({ status: "error", message: "Project not found." });
      } else {
        setAnalysisState({ status: "error", message: "Unexpected error while starting analysis." });
      }
    }
  };

  return (
    <AppLayout>
      <div className="page-container animate-fade-in">
        {/* Project selector */}
        <section className="section-spacing">
          <h3 className="font-display font-semibold text-foreground mb-6">Project</h3>
          <div className="bg-card border border-border rounded-lg p-6 lg:p-8 space-y-4">
            {projectError && (
              <div className="bg-destructive/5 border border-destructive/20 rounded-lg p-4 flex items-start gap-3">
                <AlertCircle className="w-4 h-4 text-destructive flex-shrink-0 mt-0.5" />
                <p className="text-sm text-destructive/90">{projectError}</p>
              </div>
            )}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-mono text-muted-foreground uppercase tracking-wider">Select project</label>
                <select
                  value={selectedProjectId ?? ""}
                  onChange={(e) => setSelectedProjectId(Number(e.target.value))}
                  disabled={projectsLoading || analysisState.status === "running"}
                  className="w-full mt-2 h-10 px-3 rounded-md border border-input bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="" disabled>
                    {projectsLoading ? "Loading..." : "Select"}
                  </option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs font-mono text-muted-foreground uppercase tracking-wider">Create project</label>
                <div className="flex gap-2 mt-2">
                  <Input
                    value={newProjectName}
                    onChange={(e) => setNewProjectName(e.target.value)}
                    disabled={analysisState.status === "running"}
                    className="h-10"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleCreateProject}
                    disabled={analysisState.status === "running"}
                  >
                    Create
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Upload sections */}
        <section className="section-spacing">
          <div className="space-y-8">
            <DatasetUploadBox
              label="Primary dataset"
              description="Upload the primary CSV file for analysis"
              onFileSelect={handlePrimaryFileSelect}
            />

            <DatasetUploadBox
              label="Comparison dataset"
              description="Baseline or previous period data for change detection"
              isOptional
              onFileSelect={(file) => setComparisonFile(file)}
            />
          </div>
        </section>

        {/* Schema preview loading */}
        {schemaState.status === "loading" && (
          <section className="section-spacing animate-fade-in">
            <h3 className="font-display font-semibold text-foreground mb-6">Schema preview</h3>
            <div className="rounded-lg border border-border overflow-hidden p-4 space-y-3">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          </section>
        )}

        {/* Schema preview error */}
        {schemaState.status === "error" && (
          <section className="section-spacing animate-fade-in">
            <div className="bg-destructive/5 border border-destructive/20 rounded-lg p-6 flex items-start gap-4">
              <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-destructive">Unable to preview schema</p>
                <p className="text-sm text-muted-foreground mt-1">{schemaState.message}</p>
              </div>
            </div>
          </section>
        )}

        {/* Preprocessing options — checklist §4: exactly these four */}
        <section className="section-spacing">
          <h3 className="font-display font-semibold text-foreground mb-6">
            Cleaning options
          </h3>
          <div className="bg-card border border-border rounded-lg p-6 lg:p-8">
            <div className="space-y-2">
              <ToggleOption
                label="Drop duplicates"
                description="Remove identical rows from dataset"
                checked={preprocessing.dropDuplicates}
                onCheckedChange={(checked) =>
                  setPreprocessing((prev) => ({ ...prev, dropDuplicates: checked }))
                }
                disabled={analysisState.status === "running"}
              />
              <ToggleOption
                label="Drop missing values"
                description="Remove rows with empty cells"
                checked={preprocessing.dropMissing}
                onCheckedChange={(checked) =>
                  setPreprocessing((prev) => ({ ...prev, dropMissing: checked }))
                }
                disabled={analysisState.status === "running"}
              />
              <ToggleOption
                label="Cap outliers"
                description="Limit extreme values to percentile bounds"
                checked={preprocessing.capOutliers}
                onCheckedChange={(checked) =>
                  setPreprocessing((prev) => ({ ...prev, capOutliers: checked }))
                }
                disabled={analysisState.status === "running"}
              />
              <ToggleOption
                label="Normalize column names"
                description="Standardize column names and formats"
                checked={preprocessing.normalizeColumns}
                onCheckedChange={(checked) =>
                  setPreprocessing((prev) => ({ ...prev, normalizeColumns: checked }))
                }
                disabled={analysisState.status === "running"}
              />
            </div>
          </div>
        </section>

        {/* Metric Schema selector — checklist §4 */}
        <section className="section-spacing">
          <h3 className="font-display font-semibold text-foreground mb-6">
            Metric schema
          </h3>
          <div className="bg-card border border-border rounded-lg p-6 lg:p-8 space-y-4">
            <select
              value={metricSchema}
              onChange={(e) => setMetricSchema(e.target.value as MetricSchema)}
              disabled={analysisState.status === "running"}
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
                placeholder="Enter column name"
                disabled={analysisState.status === "running"}
                className="h-10"
              />
            )}
          </div>
        </section>

        {/* Analysis error */}
        {analysisState.status === "error" && (
          <section className="animate-fade-in">
            <div className="bg-destructive/5 border border-destructive/20 rounded-lg p-6 flex items-start gap-4">
              <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-destructive">Analysis failed</p>
                <p className="text-sm text-muted-foreground mt-1">{analysisState.message}</p>
              </div>
            </div>
          </section>
        )}

        {/* Run analysis — checklist §5 */}
        <section className="pt-4">
          <Button
            size="lg"
            disabled={!canRunAnalysis}
            onClick={handleRunAnalysis}
            className="font-medium h-12 px-8"
          >
            {analysisState.status === "running" ? (
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
            <p className="text-sm text-muted-foreground mt-4">
              Upload a primary dataset to begin analysis
            </p>
          )}
        </section>
      </div>
    </AppLayout>
  );
}
