import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface MetricCardProps {
  label: string;
  value: string | number;
  delta?: string;
  deltaType?: "positive" | "negative" | "neutral";
  trend?: "up" | "down" | "flat";
  className?: string;
}

export function MetricCard({ 
  label, 
  value, 
  delta, 
  deltaType: rawDeltaType = "neutral",
  trend,
  className 
}: MetricCardProps) {
  // Map trend to deltaType if trend is provided
  const deltaType = trend 
    ? (trend === "up" ? "positive" : trend === "down" ? "negative" : "neutral")
    : rawDeltaType;

  const TrendIcon = trend === "up" ? TrendingUp : trend === "down" ? TrendingDown : trend === "flat" ? Minus : null;

  return (
    <div className={cn(
      "group bg-card border border-border rounded-lg p-5 transition-all duration-200 ease-out",
      "hover:border-primary/30 hover:shadow-md hover:-translate-y-0.5",
      className
    )}>
      <p className="text-sm text-muted-foreground font-medium mb-2 transition-colors duration-200 group-hover:text-foreground">
        {label}
      </p>
      <p className="text-2xl font-display font-semibold tracking-tight transition-colors duration-200 group-hover:text-primary">
        {value}
      </p>
      {(delta || TrendIcon) && (
        <div className={cn(
          "flex items-center gap-1.5 mt-2 transition-transform duration-200 group-hover:translate-x-0.5",
          deltaType === "positive" && "text-emerald-500",
          deltaType === "negative" && "text-destructive",
          deltaType === "neutral" && "text-muted-foreground"
        )}>
          {TrendIcon && <TrendIcon className="w-3.5 h-3.5" />}
          {delta && <span className="text-sm font-mono">{delta}</span>}
        </div>
      )}
    </div>
  );
}
