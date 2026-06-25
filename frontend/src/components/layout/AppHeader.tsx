import { useLocation, useNavigate } from "react-router-dom";
import { Moon, Sun, LogOut, Building2 } from "lucide-react";
import { useTheme } from "@/hooks/useTheme";
import { useAuth } from "@/hooks/useAuth";
import { useDefaultProject } from "@/hooks/useAnalysis";

const PAGE_TITLES: Record<string, string> = {
  "/": "Overview",
  "/datasets": "Datasets",
  "/insights": "Insights",
  "/forecast": "Forecast",
  "/margins": "Margins",
  "/retention": "Retention",
  "/comparison": "Comparison",
  "/report": "Report",
  "/history": "History",
  "/settings": "Settings",
  "/admin": "Admin",
};

export function AppHeader() {
  const location = useLocation();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const { user, logout } = useAuth();
  const { data: workspace } = useDefaultProject();
  const title = PAGE_TITLES[location.pathname] ?? "Kaizen";

  return (
    <header className="sticky top-0 z-10 h-14 border-b border-border bg-background/85 backdrop-blur supports-[backdrop-filter]:bg-background/70">
      <div className="flex h-full items-center justify-between px-6">
        <div className="flex items-center gap-3">
          <h1 className="font-display text-base font-semibold tracking-tight text-foreground">{title}</h1>
          {workspace?.name && (
            <>
              <span className="text-border" aria-hidden>/</span>
              <span className="inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-2 py-1 text-xs font-medium text-muted-foreground">
                <Building2 className="h-3 w-3" aria-hidden />
                <span className="max-w-[12rem] truncate">{workspace.name}</span>
              </span>
            </>
          )}
        </div>

        <div className="flex items-center gap-2">
          {user && (
            <span className="hidden text-xs font-mono text-muted-foreground sm:inline">{user.email}</span>
          )}
          <button
            onClick={toggleTheme}
            className="focus-calm rounded-md p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            aria-label="Toggle theme"
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
          {user && (
            <button
              onClick={() => { logout(); navigate("/login"); }}
              className="focus-calm rounded-md p-2 text-muted-foreground transition-colors hover:bg-signal-overdue/10 hover:text-signal-overdue"
              aria-label="Log out"
            >
              <LogOut className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
