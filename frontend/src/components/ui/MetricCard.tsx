import { cn } from "@/lib/utils";

interface MetricCardProps {
  label: string;
  value: string | number;
  delta?: string;
  deltaType?: "positive" | "negative" | "neutral";
  className?: string;
}

export function MetricCard({ 
  label, 
  value, 
  delta, 
  deltaType = "neutral",
  className 
}: MetricCardProps) {
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
      {delta && (
        <p className={cn(
          "text-sm font-mono mt-2 transition-transform duration-200 group-hover:translate-x-0.5",
          deltaType === "positive" && "text-primary",
          deltaType === "negative" && "text-destructive",
          deltaType === "neutral" && "text-muted-foreground"
        )}>
          {delta}
        </p>
      )}
    </div>
  );
}
