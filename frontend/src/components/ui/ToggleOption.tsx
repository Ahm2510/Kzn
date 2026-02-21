import { cn } from "@/lib/utils";
import { Switch } from "@/components/ui/switch";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { HelpCircle } from "lucide-react";

interface ToggleOptionProps {
  label: string;
  description: string;
  tooltip?: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  disabled?: boolean;
  className?: string;
}

export function ToggleOption({
  label,
  description,
  tooltip,
  checked,
  onCheckedChange,
  disabled = false,
  className,
}: ToggleOptionProps) {
  return (
    <div className={cn(
      "group flex items-start justify-between gap-6 py-5 border-b border-border/60 last:border-0 transition-all duration-200",
      "hover:bg-muted/30 hover:px-3 hover:-mx-3 hover:rounded-lg",
      disabled && "opacity-50 pointer-events-none",
      className
    )}>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-foreground transition-colors duration-200 group-hover:text-primary cursor-pointer">
            {label}
          </label>
          {tooltip && (
            <Tooltip>
              <TooltipTrigger asChild>
                <HelpCircle className="w-3.5 h-3.5 text-muted-foreground cursor-help transition-all duration-200 hover:text-primary hover:scale-110" />
              </TooltipTrigger>
              <TooltipContent side="top" className="max-w-xs">
                <p className="text-xs">{tooltip}</p>
              </TooltipContent>
            </Tooltip>
          )}
        </div>
        <p className="text-sm text-muted-foreground mt-0.5 transition-colors duration-200 group-hover:text-muted-foreground/80">
          {description}
        </p>
      </div>
      <Switch
        checked={checked}
        onCheckedChange={onCheckedChange}
        disabled={disabled}
        className="flex-shrink-0 transition-transform duration-200 hover:scale-105"
      />
    </div>
  );
}
