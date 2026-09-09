import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Moon, Sun, LogOut, Building2, ChevronDown, Plus, Check } from "lucide-react";
import { useTheme } from "@/hooks/useTheme";
import { useAuth } from "@/hooks/useAuth";
import { useActiveWorkspace, useCreateWorkspace } from "@/hooks/useWorkspaces";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";

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
  const { workspaces, activeWorkspace, activeWorkspaceId, setActiveWorkspaceId } = useActiveWorkspace();
  const createWorkspace = useCreateWorkspace();

  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [newClientName, setNewClientName] = useState("");
  const [newFirmName, setNewFirmName] = useState("");

  const title = PAGE_TITLES[location.pathname] ?? "Kaizen";

  const handleCreateClient = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newClientName.trim()) {
      toast.error("Client name is required.");
      return;
    }

    try {
      const created = await createWorkspace.mutateAsync({
        name: newClientName.trim(),
        firmName: newFirmName.trim(),
      });
      setActiveWorkspaceId(created.id);
      toast.success(`Client "${created.name}" created.`);
      setNewClientName("");
      setNewFirmName("");
      setIsAddModalOpen(false);
    } catch (err: unknown) {
      const error = err as Error;
      toast.error(error.message || "Failed to create client.");
    }
  };

  return (
    <>
      <header className="sticky top-0 z-10 h-14 border-b border-border bg-background/85 backdrop-blur supports-[backdrop-filter]:bg-background/70">
        <div className="flex h-full items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <h1 className="font-display text-base font-semibold tracking-tight text-foreground">{title}</h1>

            <span className="text-border" aria-hidden>/</span>

            {/* Client Switcher Dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="inline-flex items-center gap-2 rounded-md border border-border bg-card px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:bg-muted focus-calm">
                  <Building2 className="h-3.5 w-3.5 text-primary" aria-hidden />
                  <span className="max-w-[12rem] truncate">
                    {activeWorkspace?.name || "Select Client"}
                  </span>
                  <ChevronDown className="h-3 w-3 text-muted-foreground" aria-hidden />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="w-56">
                <DropdownMenuLabel className="text-[10px] font-mono text-muted-foreground uppercase">
                  Select Client
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                {workspaces.map((w) => {
                  const isSelected = w.id === activeWorkspaceId;
                  return (
                    <DropdownMenuItem
                      key={w.id}
                      onClick={() => setActiveWorkspaceId(w.id)}
                      className="flex items-center justify-between cursor-pointer text-xs"
                    >
                      <div className="flex flex-col min-w-0 pr-2">
                        <span className={isSelected ? "font-semibold text-foreground" : "text-muted-foreground"}>
                          {w.name}
                        </span>
                        {w.firm_name && (
                          <span className="text-[10px] text-muted-foreground/75 truncate">
                            {w.firm_name}
                          </span>
                        )}
                      </div>
                      {isSelected && <Check className="h-3.5 w-3.5 text-primary shrink-0" />}
                    </DropdownMenuItem>
                  );
                })}
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={() => setIsAddModalOpen(true)}
                  className="cursor-pointer text-xs text-primary font-medium focus:text-primary"
                >
                  <Plus className="h-3.5 w-3.5 mr-1.5" />
                  Add Client
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
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

      {/* Add Client Dialog */}
      <Dialog open={isAddModalOpen} onOpenChange={setIsAddModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-lg font-display font-bold">Add Client</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreateClient} className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label htmlFor="client-name">Client Name *</Label>
              <Input
                id="client-name"
                placeholder="e.g. Apex Traders Pvt Ltd"
                value={newClientName}
                onChange={(e) => setNewClientName(e.target.value)}
                autoFocus
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="firm-name">CA Firm Header Name (Optional White-Labeling)</Label>
              <Input
                id="firm-name"
                placeholder="e.g. Sharma & Associates CA Firm"
                value={newFirmName}
                onChange={(e) => setNewFirmName(e.target.value)}
              />
              <p className="text-[11px] text-muted-foreground">
                Appears on generated PDF report headers for this client.
              </p>
            </div>
            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={() => setIsAddModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createWorkspace.isPending}>
                {createWorkspace.isPending ? "Creating..." : "Create Client"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
