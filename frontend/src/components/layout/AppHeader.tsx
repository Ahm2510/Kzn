import { useLocation, useNavigate } from "react-router-dom";
import { Moon, Sun, LogOut, ShieldCheck } from "lucide-react";
import { useTheme } from "@/hooks/useTheme";
import { useAuth } from "@/hooks/useAuth";
import { cn } from "@/lib/utils";

const PAGE_TITLES: Record<string, string> = {
  "/": "Overview",
  "/datasets": "Datasets & Preprocessing",
  "/insights": "Insights",
  "/comparison": "Comparison",
  "/report": "Report",
  "/history": "History",
  "/settings": "Settings",
  "/admin": "Admin Panel",
};

export function AppHeader() {
  const location = useLocation();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const { user, logout, isAdmin } = useAuth();
  const title = PAGE_TITLES[location.pathname] ?? "Kaizen.";

  return (
    <header className="h-14 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-10">
      <div className="flex items-center justify-between h-full px-6">
        <h1 className="font-display font-semibold text-lg text-foreground">{title}</h1>
        <div className="flex items-center gap-3">
          {user && (
            <span className="text-xs text-muted-foreground font-mono">{user.email}</span>
          )}
          {user && (
            <span className={cn(
              "text-[10px] font-mono px-1.5 py-0.5 rounded border",
              user.role === "admin"
                ? "border-primary/40 text-primary bg-primary/10"
                : "border-border text-muted-foreground bg-muted/30"
            )}>
              {user.role.toUpperCase()}
            </span>
          )}
          {isAdmin && (
            <button
              onClick={() => navigate("/admin")}
              className="p-2 rounded-md hover:bg-muted transition-all duration-200"
              title="Admin Panel"
            >
              <ShieldCheck className="w-4 h-4 text-muted-foreground" />
            </button>
          )}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-md hover:bg-muted transition-all duration-200"
            aria-label="Toggle theme"
          >
            {theme === "dark" ? (
              <Sun className="w-4 h-4 text-muted-foreground" />
            ) : (
              <Moon className="w-4 h-4 text-muted-foreground" />
            )}
          </button>
          {user && (
            <button
              onClick={() => { logout(); navigate("/login"); }}
              className="p-2 rounded-md hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-all duration-200"
              aria-label="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
