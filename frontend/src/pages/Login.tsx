import { useState, useRef, useEffect } from "react";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/hooks/useAuth";
import { cn } from "@/lib/utils";
import { Lock, ArrowRight } from "lucide-react";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [focusedField, setFocusedField] = useState<string | null>(null);
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [isHovering, setIsHovering] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [showForgot, setShowForgot] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);
  
  const navigate = useNavigate();
  const { login, isAuthenticated } = useAuth();

  useEffect(() => {
    if (isAuthenticated) {
      navigate("/");
    }
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    setMousePosition({
      x: ((e.clientX - rect.left) / rect.width) * 100,
      y: ((e.clientY - rect.top) / rect.height) * 100,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);
    
    const result = await login(email, password);
    
    if (result.success) {
      navigate("/");
    } else {
      setError(result.error || "Authentication failed.");
      setIsLoading(false);
    }
  };

  return (
    <div 
      ref={containerRef}
      onMouseMove={handleMouseMove}
      className="min-h-screen bg-background flex relative overflow-hidden"
    >
      {/* Animated background gradient that follows mouse */}
      <div 
        className="absolute inset-0 opacity-40 dark:opacity-30 transition-opacity duration-1000 pointer-events-none"
        style={{
          background: `radial-gradient(circle at ${mousePosition.x}% ${mousePosition.y}%, hsl(var(--primary) / 0.12) 0%, transparent 50%)`,
        }}
      />

      {/* Left panel - branded statement (60%) */}
      <div className={cn(
        "hidden lg:flex lg:w-[60%] bg-card relative overflow-hidden",
        "transition-all duration-1000 ease-out",
        mounted ? "opacity-100 translate-x-0" : "opacity-0 -translate-x-8"
      )}>
        {/* Animated mesh gradient - teal & gold tones */}
        <div className="absolute inset-0">
          <div 
            className="absolute inset-0 opacity-70"
            style={{
              background: `
                radial-gradient(ellipse at 20% 30%, hsl(var(--primary) / 0.12) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 70%, hsl(var(--secondary) / 0.08) 0%, transparent 50%),
                radial-gradient(ellipse at 50% 50%, hsl(var(--muted) / 0.05) 0%, transparent 70%)
              `,
            }}
          />
          {/* Floating orbs with teal tones */}
          <div className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full blur-3xl animate-orb-drift"
            style={{ background: 'radial-gradient(circle, hsl(var(--primary) / 0.08) 0%, transparent 70%)' }}
          />
          <div className="absolute bottom-1/4 right-1/4 w-64 h-64 rounded-full blur-3xl animate-orb-drift"
            style={{ background: 'radial-gradient(circle, hsl(var(--secondary) / 0.06) 0%, transparent 70%)', animationDelay: '-7s' }}
          />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-80 h-80 rounded-full blur-3xl animate-breathe"
            style={{ background: 'radial-gradient(circle, hsl(var(--primary) / 0.04) 0%, transparent 60%)' }}
          />
        </div>
        
        {/* Grid pattern overlay */}
        <div 
          className="absolute inset-0 opacity-[0.015] dark:opacity-[0.025]"
          style={{
            backgroundImage: `
              linear-gradient(hsl(var(--foreground)) 1px, transparent 1px),
              linear-gradient(90deg, hsl(var(--foreground)) 1px, transparent 1px)
            `,
            backgroundSize: '60px 60px',
          }}
        />
        
        {/* Content */}
        <div className="relative z-10 flex flex-col justify-center px-16 xl:px-24">
          {/* Wordmark with animation */}
          <div className={cn(
            "mb-20 transition-all duration-1000 delay-200",
            mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
          )}>
            <h1 className="font-display text-6xl xl:text-7xl font-bold text-foreground tracking-tight leading-none">
              Kaizen<span className="text-primary">.</span>
            </h1>
          </div>
          
          {/* Statement with stagger animation */}
          <div className={cn(
            "transition-all duration-1000 delay-400",
            mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
          )}>
            <p className="text-2xl xl:text-3xl text-muted-foreground leading-relaxed max-w-lg font-light">
              Analytical control plane for{" "}
              <span className="text-foreground font-normal">decision-grade</span> data.
            </p>
          </div>
          
          {/* Decorative element with gold accent */}
          <div className={cn(
            "mt-24 flex items-center gap-4 transition-all duration-1000 delay-600",
            mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
          )}>
            <div className="w-16 h-px bg-gradient-to-r from-secondary/60 to-transparent" />
            <span className="text-xs text-muted-foreground/60 font-mono uppercase tracking-[0.2em]">
              Insights Engine
            </span>
          </div>
        </div>
        
        {/* Animated border accent - teal glow */}
        <div className="absolute right-0 top-0 bottom-0 w-px overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-primary/40 to-transparent animate-shimmer" />
        </div>
      </div>

      {/* Right panel - login form (40%) */}
      <div className="flex-1 flex items-center justify-center p-8 lg:p-16 relative">
        {/* Subtle pattern */}
        <div 
          className="absolute inset-0 opacity-[0.015] dark:opacity-[0.03]"
          style={{
            backgroundImage: `radial-gradient(hsl(var(--foreground)) 1px, transparent 1px)`,
            backgroundSize: '24px 24px',
          }}
        />

        {/* Floating panel */}
        <div className={cn(
          "w-full max-w-md relative z-10",
          "transition-all duration-1000 delay-300",
          mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
        )}>
          {/* Mobile branding */}
          <div className="lg:hidden mb-16">
            <h1 className="font-display text-4xl font-bold text-foreground tracking-tight">
              Kaizen<span className="text-primary">.</span>
            </h1>
            <p className="text-muted-foreground mt-3 text-lg">
              Analytical control plane for decision-grade data.
            </p>
          </div>

          {/* Login header */}
          <div className="mb-12">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-lg bg-muted/50">
                <Lock className="w-4 h-4 text-muted-foreground" />
              </div>
              <span className="text-xs font-mono text-muted-foreground/70 uppercase tracking-wider">
                Secure Access
              </span>
            </div>
            <h2 className="font-display text-3xl font-semibold text-foreground mb-4">
              Welcome back
            </h2>
            <p className="text-muted-foreground leading-relaxed">
              Access is by invitation only. Enter your credentials to continue to the control plane.
            </p>
          </div>

          {!showForgot ? (
            <>
              {/* Error state */}
              {error && (
                <div className="mb-8 p-4 bg-destructive/5 border border-destructive/20 rounded-xl animate-fade-in backdrop-blur-sm">
                  <p className="text-sm text-destructive/90 font-medium">
                    {error}
                  </p>
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="space-y-2">
                  <label 
                    htmlFor="email" 
                    className={cn(
                      "text-sm font-medium transition-all duration-500",
                      focusedField === "email" ? "text-primary" : "text-foreground"
                    )}
                  >
                    Email address
                  </label>
                  <div className="relative">
                    <Input
                      id="email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      onFocus={() => setFocusedField("email")}
                      onBlur={() => setFocusedField(null)}
                      placeholder="you@organization.com"
                      required
                      className={cn(
                        "h-14 text-base px-4 rounded-xl border-2",
                        "transition-all duration-500 ease-out",
                        "placeholder:text-muted-foreground/40",
                        focusedField === "email" 
                          ? "border-primary shadow-lg shadow-primary/10 bg-background" 
                          : "border-border/60 bg-muted/30 hover:bg-muted/50"
                      )}
                    />
                    <div className={cn(
                      "absolute inset-0 rounded-xl pointer-events-none transition-opacity duration-500",
                      focusedField === "email" ? "opacity-100" : "opacity-0"
                    )}
                      style={{
                        background: `linear-gradient(135deg, hsl(var(--primary) / 0.05) 0%, transparent 50%)`,
                      }}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <label 
                    htmlFor="password" 
                    className={cn(
                      "text-sm font-medium transition-all duration-500",
                      focusedField === "password" ? "text-primary" : "text-foreground"
                    )}
                  >
                    Password
                  </label>
                  <div className="relative">
                    <Input
                      id="password"
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      onFocus={() => setFocusedField("password")}
                      onBlur={() => setFocusedField(null)}
                      placeholder="••••••••••••"
                      required
                      className={cn(
                        "h-14 text-base px-4 rounded-xl border-2",
                        "transition-all duration-500 ease-out",
                        "placeholder:text-muted-foreground/40",
                        focusedField === "password" 
                          ? "border-primary shadow-lg shadow-primary/10 bg-background" 
                          : "border-border/60 bg-muted/30 hover:bg-muted/50"
                      )}
                    />
                    <div className={cn(
                      "absolute inset-0 rounded-xl pointer-events-none transition-opacity duration-500",
                      focusedField === "password" ? "opacity-100" : "opacity-0"
                    )}
                      style={{
                        background: `linear-gradient(135deg, hsl(var(--primary) / 0.05) 0%, transparent 50%)`,
                      }}
                    />
                  </div>
                </div>

                <div className="pt-4">
                  <Button 
                    type="submit" 
                    onMouseEnter={() => setIsHovering(true)}
                    onMouseLeave={() => setIsHovering(false)}
                    className={cn(
                      "w-full h-14 text-base font-medium rounded-xl relative overflow-hidden group",
                      "transition-all duration-700 ease-out",
                      "active:scale-[0.98] active:transition-transform active:duration-150",
                      "shadow-lg shadow-primary/20 hover:shadow-xl hover:shadow-primary/30",
                      isLoading && "opacity-90"
                    )}
                    disabled={isLoading}
                  >
                    {/* Button gradient animation */}
                    <div className={cn(
                      "absolute inset-0 bg-gradient-to-r from-primary via-primary/90 to-primary opacity-0 transition-opacity duration-500",
                      isHovering && !isLoading && "opacity-100"
                    )} />
                    
                    <span className="relative z-10 flex items-center justify-center gap-3">
                      {isLoading ? (
                        <>
                          <div className="flex gap-1">
                            <div className="w-2 h-2 bg-primary-foreground/80 rounded-full animate-bounce-slow" style={{ animationDelay: '0ms' }} />
                            <div className="w-2 h-2 bg-primary-foreground/80 rounded-full animate-bounce-slow" style={{ animationDelay: '150ms' }} />
                            <div className="w-2 h-2 bg-primary-foreground/80 rounded-full animate-bounce-slow" style={{ animationDelay: '300ms' }} />
                          </div>
                          <span>Authenticating</span>
                        </>
                      ) : (
                        <>
                          <span>Continue to Kaizen.</span>
                          <ArrowRight className={cn(
                            "w-4 h-4 transition-transform duration-500",
                            isHovering && "translate-x-1"
                          )} />
                        </>
                      )}
                    </span>
                  </Button>
                </div>
              </form>
              <div className="text-center mt-4">
                <button
                  type="button"
                  onClick={() => setShowForgot(true)}
                  className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  Forgot your password?
                </button>
              </div>
            </>
          ) : (
            <div className="space-y-6">
              <div>
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2 rounded-lg bg-muted/50">
                    <Lock className="w-4 h-4 text-muted-foreground" />
                  </div>
                  <span className="text-xs font-mono text-muted-foreground/70 uppercase tracking-wider">
                    Password Reset
                  </span>
                </div>
                <h2 className="font-display text-3xl font-semibold text-foreground mb-4">
                  Reset Password
                </h2>
                <p className="text-muted-foreground leading-relaxed">
                  Enter your email and your administrator will be notified to reset your password.
                </p>
              </div>
              <div className="space-y-2">
                <label htmlFor="forgot-email" className="text-sm font-medium text-foreground">
                  Email address
                </label>
                <Input
                  id="forgot-email"
                  type="email"
                  placeholder="your@email.com"
                  value={forgotEmail}
                  onChange={(e) => setForgotEmail(e.target.value)}
                  className={cn(
                    "h-14 text-base px-4 rounded-xl border-2",
                    "transition-all duration-500 ease-out",
                    "placeholder:text-muted-foreground/40",
                    "border-border/60 bg-muted/30 hover:bg-muted/50 focus:border-primary focus:shadow-lg focus:shadow-primary/10 focus:bg-background"
                  )}
                />
              </div>
              <Button
                type="button"
                className={cn(
                  "w-full h-14 text-base font-medium rounded-xl",
                  "shadow-lg shadow-primary/20"
                )}
                onClick={() => {
                  toast.info("Password reset is managed by your administrator. Please contact them directly.");
                  setShowForgot(false);
                }}
              >
                Send Reset Request
              </Button>
              <div className="text-center">
                <button
                  type="button"
                  onClick={() => setShowForgot(false)}
                  className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  ← Back to sign in
                </button>
              </div>
            </div>
          )}

          {/* Footer note */}
          <div className="mt-16 pt-8 border-t border-border/50">
            <p className="text-sm text-muted-foreground/60 leading-relaxed">
              This system is restricted to authorized personnel. Unauthorized access attempts are logged and monitored.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
