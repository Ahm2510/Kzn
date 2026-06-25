/**
 * Designed empty / error / idle state. Calm and direct: a single quiet icon
 * tile, a clear sentence about what to do next, and one action. No decorative
 * orbs, blur, or float — restraint is the enterprise signal.
 */
import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center px-6 py-16 text-center animate-fade-in",
        className
      )}
    >
      <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-lg border border-border bg-muted/50">
        <Icon className="h-5 w-5 text-muted-foreground" aria-hidden />
      </div>
      <h3 className="mb-2 font-display text-lg font-semibold text-foreground">{title}</h3>
      <p className="mb-7 max-w-sm text-sm leading-relaxed text-muted-foreground">{description}</p>
      {action && <div>{action}</div>}
    </div>
  );
}
