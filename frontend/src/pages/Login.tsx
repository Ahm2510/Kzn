import { useState, useEffect } from "react";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/hooks/useAuth";
import { ArrowRight, OctagonAlert } from "lucide-react";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForgot, setShowForgot] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");

  const navigate = useNavigate();
  const { login, isAuthenticated } = useAuth();

  useEffect(() => {
    if (isAuthenticated) navigate("/");
  }, [isAuthenticated, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);
    const result = await login(email, password);
    if (result.success) {
      navigate("/");
    } else {
      setError(result.error || "We couldn't sign you in. Check your email and password and try again.");
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-background">
      {/* Left: brand statement — calm, no decoration */}
      <div className="hidden w-[52%] flex-col justify-between border-r border-border bg-card p-14 lg:flex xl:p-20">
        <span className="font-display text-2xl font-bold tracking-tight text-foreground">
          Kaizen<span className="text-primary">.</span>
        </span>
        <div className="max-w-lg">
          <h1 className="font-display text-4xl font-semibold leading-tight tracking-tight text-foreground xl:text-5xl">
            Know who's churning, what stock is dead, and which payments are overdue.
          </h1>
          <p className="mt-6 text-lg leading-relaxed text-muted-foreground">
            Financial health audits for your clients, ready in minutes. Built to be read in ten
            seconds, not studied for an hour.
          </p>
        </div>
        <p className="text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
          Financial Health Intelligence
        </p>
      </div>

      {/* Right: form */}
      <div className="flex flex-1 items-center justify-center p-8 lg:p-16">
        <div className="w-full max-w-sm">
          <div className="mb-10 lg:hidden">
            <span className="font-display text-2xl font-bold tracking-tight text-foreground">
              Kaizen<span className="text-primary">.</span>
            </span>
          </div>

          {!showForgot ? (
            <>
              <div className="mb-8">
                <h2 className="font-display text-2xl font-semibold tracking-tight text-foreground">Sign in</h2>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  Access is by invitation. Enter your credentials to continue.
                </p>
              </div>

              {error && (
                <div className="mb-6 flex items-start gap-2.5 rounded-lg border border-signal-overdue/30 bg-signal-overdue/[0.06] p-3.5 animate-fade-in">
                  <OctagonAlert className="mt-0.5 h-4 w-4 shrink-0 text-signal-overdue" aria-hidden />
                  <p className="text-sm text-foreground">{error}</p>
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-5">
                <div className="space-y-2">
                  <label htmlFor="email" className="text-sm font-medium text-foreground">Email address</label>
                  <Input
                    id="email"
                    type="email"
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@organization.in"
                    required
                    className="h-11"
                  />
                </div>
                <div className="space-y-2">
                  <label htmlFor="password" className="text-sm font-medium text-foreground">Password</label>
                  <Input
                    id="password"
                    type="password"
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Your password"
                    required
                    className="h-11"
                  />
                </div>
                <Button type="submit" disabled={isLoading} className="group h-11 w-full">
                  {isLoading ? (
                    "Signing in"
                  ) : (
                    <span className="inline-flex items-center gap-2">
                      Continue
                      <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                    </span>
                  )}
                </Button>
              </form>

              <button
                type="button"
                onClick={() => setShowForgot(true)}
                className="focus-calm mt-4 rounded text-xs text-muted-foreground transition-colors hover:text-foreground"
              >
                Forgot your password?
              </button>
            </>
          ) : (
            <div className="space-y-5">
              <div>
                <h2 className="font-display text-2xl font-semibold tracking-tight text-foreground">Reset password</h2>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  Enter your email and your administrator will be notified to reset your password.
                </p>
              </div>
              <div className="space-y-2">
                <label htmlFor="forgot-email" className="text-sm font-medium text-foreground">Email address</label>
                <Input
                  id="forgot-email"
                  type="email"
                  autoComplete="email"
                  placeholder="you@organization.in"
                  value={forgotEmail}
                  onChange={(e) => setForgotEmail(e.target.value)}
                  className="h-11"
                />
              </div>
              <Button
                type="button"
                className="h-11 w-full"
                onClick={() => {
                  toast.info("Password resets are handled by your administrator. Please contact them directly.");
                  setShowForgot(false);
                }}
              >
                Send reset request
              </Button>
              <button
                type="button"
                onClick={() => setShowForgot(false)}
                className="focus-calm rounded text-xs text-muted-foreground transition-colors hover:text-foreground"
              >
                Back to sign in
              </button>
            </div>
          )}

          <p className="mt-12 border-t border-border pt-6 text-xs leading-relaxed text-muted-foreground">
            This system is restricted to authorized personnel. Access attempts are logged.
          </p>
        </div>
      </div>
    </div>
  );
}
