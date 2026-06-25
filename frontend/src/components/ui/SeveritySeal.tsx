/**
 * SeveritySeal — the product's signature risk indicator.
 *
 * A filled seal with a distinct glyph per level, so severity is legible by
 * shape as well as colour (never colour alone). Used identically across churn,
 * dead stock, receivables, and alerts so the pattern is learned once and read
 * everywhere. Deliberately NOT a coloured left-border stripe (an absolute ban).
 */
import { OctagonAlert, TriangleAlert, Check, Minus, type LucideIcon } from "lucide-react";
import { useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";

export type SeverityLevel = "overdue" | "slowing" | "clear" | "neutral";

const MAP: Record<SeverityLevel, { bg: string; glyph: LucideIcon; label: string }> = {
  overdue: { bg: "bg-signal-overdue", glyph: OctagonAlert, label: "Overdue" },
  slowing: { bg: "bg-signal-slowing", glyph: TriangleAlert, label: "Needs attention" },
  clear: { bg: "bg-signal-clear", glyph: Check, label: "On track" },
  neutral: { bg: "bg-muted-foreground/55", glyph: Minus, label: "Neutral" },
};

const SIZES = {
  sm: { box: "h-5 w-5 rounded-[5px]", icon: "h-3 w-3" },
  md: { box: "h-7 w-7 rounded-md", icon: "h-4 w-4" },
  lg: { box: "h-9 w-9 rounded-md", icon: "h-5 w-5" },
};

interface SeveritySealProps {
  level: SeverityLevel;
  size?: keyof typeof SIZES;
  /** Subtle opacity breathing — reserve for the single highest-severity item. */
  pulse?: boolean;
  className?: string;
}

export function SeveritySeal({ level, size = "md", pulse = false, className }: SeveritySealProps) {
  const reduce = useReducedMotion();
  const { bg, glyph: Glyph, label } = MAP[level];
  const s = SIZES[size];

  return (
    <span
      role="img"
      aria-label={label}
      className={cn(
        "inline-flex shrink-0 items-center justify-center text-white/95 shadow-sm",
        bg,
        s.box,
        pulse && !reduce && "animate-seal-breathe",
        className
      )}
    >
      <Glyph className={s.icon} strokeWidth={2.5} aria-hidden />
    </span>
  );
}

/** Small inline keycap tag in a signal colour (for severity labels in rows). */
export function SignalTag({ level, children }: { level: SeverityLevel; children: React.ReactNode }) {
  const tone: Record<SeverityLevel, string> = {
    overdue: "text-signal-overdue",
    slowing: "text-signal-slowing",
    clear: "text-signal-clear",
    neutral: "text-muted-foreground",
  };
  return (
    <span className={cn("text-[10px] font-mono font-semibold uppercase tracking-[0.12em]", tone[level])}>
      {children}
    </span>
  );
}
