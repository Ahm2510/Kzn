import { cn } from "@/lib/utils";

export type InsightSeverity = "high" | "medium" | "low";

interface InsightCardProps {
  title: string;
  description: string;
  driver?: string;
  implication?: string;
  actionDirection?: string;
  confidence?: string;
  confidenceBasis?: string;
  severity: InsightSeverity;
  className?: string;
}

export function InsightCard({
  title,
  description,
  driver,
  implication,
  actionDirection,
  confidence,
  confidenceBasis,
  severity,
  className,
}: InsightCardProps) {
  const hasEnrichment = driver || implication || actionDirection || confidenceBasis;

  return (
    <div
      className={cn(
        "bg-card border border-border rounded-lg p-6 transition-all duration-200 hover:border-primary/30 hover:shadow-md hover:-translate-y-0.5",
        severity === "high" && "border-l-2 border-l-destructive",
        severity === "medium" && "border-l-2 border-l-gold",
        severity === "low" && "border-l-2 border-l-primary",
        className
      )}
    >
      <div className="space-y-4">
        {/* Title + Confidence badge */}
        <div className="flex items-start justify-between gap-3">
          <h4 className="font-display font-semibold text-foreground leading-snug">
            {title}
          </h4>
          {confidence && (
            <span className={cn(
              "shrink-0 text-xs font-mono px-2 py-0.5 rounded",
              confidence.toUpperCase() === "HIGH" && "bg-destructive/10 text-destructive",
              confidence.toUpperCase() === "MEDIUM" && "bg-gold/10 text-gold",
              confidence.toUpperCase() === "LOW" && "bg-primary/10 text-primary",
              !["HIGH", "MEDIUM", "LOW"].includes(confidence.toUpperCase()) && "bg-muted/50 text-muted-foreground"
            )}>
              {confidence.toUpperCase()}
            </span>
          )}
        </div>

        {/* Description */}
        <p className="text-sm text-muted-foreground leading-relaxed">
          {description}
        </p>

        {/* Structured fields — only render if at least one is populated */}
        {hasEnrichment && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-border/60">
            {driver && (
              <div className="text-xs">
                <span className="text-muted-foreground">Driver: </span>
                <span className="text-foreground">{driver}</span>
              </div>
            )}
            {implication && (
              <div className="text-xs">
                <span className="text-muted-foreground">Implication: </span>
                <span className="text-foreground">{implication}</span>
              </div>
            )}
            {actionDirection && (
              <div className="text-xs">
                <span className="text-muted-foreground">Action: </span>
                <span className="text-primary font-medium">{actionDirection}</span>
              </div>
            )}
            {confidenceBasis && (
              <div className="text-xs">
                <span className="text-muted-foreground">Confidence Basis: </span>
                <span className="text-foreground">{confidenceBasis}</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
