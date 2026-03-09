import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div className={cn(
      "flex flex-col items-center justify-center text-center py-16 px-6 relative overflow-hidden",
      className
    )}>
      {/* Fluid background decorations */}
      <div className="absolute inset-0 pointer-events-none">
        {/* Primary orb */}
        <div 
          className="absolute w-96 h-96 rounded-full blur-3xl animate-orb-drift"
          style={{
            background: 'radial-gradient(circle, hsl(var(--primary) / 0.08) 0%, transparent 70%)',
            top: '10%',
            left: '20%',
          }}
        />
        {/* Secondary orb */}
        <div 
          className="absolute w-72 h-72 rounded-full blur-3xl animate-orb-drift"
          style={{
            background: 'radial-gradient(circle, hsl(var(--secondary) / 0.06) 0%, transparent 70%)',
            bottom: '15%',
            right: '15%',
            animationDelay: '-5s',
          }}
        />
        {/* Accent orb */}
        <div 
          className="absolute w-48 h-48 rounded-full blur-2xl animate-breathe"
          style={{
            background: 'radial-gradient(circle, hsl(var(--muted) / 0.05) 0%, transparent 70%)',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
          }}
        />
        
        {/* Subtle grid pattern */}
        <div 
          className="absolute inset-0 opacity-[0.015] dark:opacity-[0.03]"
          style={{
            backgroundImage: `
              linear-gradient(hsl(var(--foreground)) 1px, transparent 1px),
              linear-gradient(90deg, hsl(var(--foreground)) 1px, transparent 1px)
            `,
            backgroundSize: '60px 60px',
          }}
        />
      </div>

      {/* Content with animation */}
      <div className="relative z-10 animate-slide-up-fade">
        <div className="relative mb-6">
          {/* Glowing ring behind icon */}
          <div className="absolute inset-0 w-16 h-16 mx-auto rounded-full bg-primary/10 blur-xl animate-pulse-subtle" />
          <div className="w-16 h-16 mx-auto rounded-full bg-gradient-to-br from-muted/40 to-muted/20 flex items-center justify-center backdrop-blur-sm border border-border/50">
            <Icon className="w-7 h-7 text-muted-foreground animate-float-gentle" />
          </div>
        </div>
        
        <h3 className="font-display font-semibold text-foreground mb-3 text-lg">
          {title}
        </h3>
        <p className="text-sm text-muted-foreground max-w-sm mb-8 leading-relaxed">
          {description}
        </p>
        
        {action && (
          <div className="relative">
            {/* Subtle glow behind button */}
            <div className="absolute inset-0 bg-primary/20 blur-xl rounded-lg opacity-0 group-hover:opacity-100 transition-opacity" />
            {action}
          </div>
        )}
      </div>

      {/* Decorative dots pattern */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex gap-2">
        <div className="w-1 h-1 rounded-full bg-muted-foreground/20 animate-pulse-subtle" style={{ animationDelay: '0s' }} />
        <div className="w-1 h-1 rounded-full bg-muted-foreground/30 animate-pulse-subtle" style={{ animationDelay: '0.5s' }} />
        <div className="w-1 h-1 rounded-full bg-muted-foreground/20 animate-pulse-subtle" style={{ animationDelay: '1s' }} />
      </div>
    </div>
  );
}
