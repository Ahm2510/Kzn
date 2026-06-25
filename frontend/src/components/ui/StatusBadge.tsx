import { cn } from "@/lib/utils";

type StatusType = "pending" | "processing" | "complete" | "error" | "idle" | "warning";

interface StatusBadgeProps {
  status: StatusType;
  label?: string;
  className?: string;
}

const statusConfig: Record<StatusType, { label: string; className: string }> = {
  idle: {
    label: "Idle",
    className: "bg-muted/30 text-muted-foreground",
  },
  pending: {
    label: "Pending",
    className: "bg-muted/30 text-muted-foreground",
  },
  processing: {
    label: "Processing",
    className: "bg-primary/10 text-primary animate-pulse-slow",
  },
  complete: {
    label: "Complete",
    className: "bg-primary/10 text-primary",
  },
  error: {
    label: "Error",
    className: "bg-destructive/10 text-destructive",
  },
  warning: {
    label: "Warning",
    className: "bg-amber-500/10 text-amber-500",
  },
};

export function StatusBadge({ status, label, className }: StatusBadgeProps) {
  const config = statusConfig[status];
  
  return (
    <span className={cn(
      "inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium transition-all duration-200",
      "hover:scale-105 hover:shadow-sm",
      config.className,
      className
    )}>
      {status === "processing" && (
        <span className="w-1.5 h-1.5 rounded-full bg-current mr-2 animate-pulse" />
      )}
      {label || config.label}
    </span>
  );
}
