import { useState, useMemo, useEffect } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { useAuth } from "@/hooks/useAuth";
import { useTheme } from "@/hooks/useTheme";
import { useActiveWorkspace, useUpdateWorkspace } from "@/hooks/useWorkspaces";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { LogOut, ShieldAlert, Key, User as UserIcon, Moon, Sun, ShieldCheck, Building2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";
import { cn } from "@/lib/utils";

const APP_VERSION = "1.0.0";
const ENVIRONMENT = import.meta.env.MODE || "development";

export default function Settings() {
  const { user, logout, changePassword, isAdmin } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { activeWorkspace } = useActiveWorkspace();
  const updateWorkspace = useUpdateWorkspace();
  const navigate = useNavigate();

  // Branding fields
  const [clientName, setClientName] = useState(activeWorkspace?.name || "");
  const [firmName, setFirmName] = useState(activeWorkspace?.firm_name || "");
  const [isSavingBranding, setIsSavingBranding] = useState(false);

  useEffect(() => {
    if (activeWorkspace) {
      setClientName(activeWorkspace.name);
      setFirmName(activeWorkspace.firm_name || "");
    }
  }, [activeWorkspace]);

  const handleBrandingSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspace) return;
    if (!clientName.trim()) {
      toast.error("Client name is required.");
      return;
    }
    setIsSavingBranding(true);
    try {
      await updateWorkspace.mutateAsync({
        id: activeWorkspace.id,
        data: { name: clientName.trim(), firm_name: firmName.trim() },
      });
      toast.success("Client & report branding updated!");
    } catch (err: unknown) {
      const error = err as Error;
      toast.error(error.message || "Failed to update client branding.");
    } finally {
      setIsSavingBranding(false);
    }
  };

  // Password fields
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isChanging, setIsChanging] = useState(false);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  // Live password strength calculation
  const strength = useMemo(() => {
    if (!newPassword) return { score: 0, label: "Empty", color: "bg-muted" };
    let score = 0;
    if (newPassword.length >= 8) score++;
    if (/[A-Z]/.test(newPassword)) score++;
    if (/[a-z]/.test(newPassword)) score++;
    if (/[0-9]/.test(newPassword)) score++;
    if (/[^A-Za-z0-9]/.test(newPassword)) score++;

    if (score <= 2) return { score, label: "Weak", color: "bg-red-500", progress: "w-1/3" };
    if (score <= 4) return { score, label: "Fair", color: "bg-yellow-500", progress: "w-2/3" };
    return { score, label: "Strong", color: "bg-emerald-500", progress: "w-full" };
  }, [newPassword]);

  const passwordSchema = z.object({
    oldPassword: z.string().min(1, "Current password is required."),
    newPassword: z.string().min(8, "New password must be at least 8 characters long."),
    confirmPassword: z.string()
  }).refine((data) => data.newPassword === data.confirmPassword, {
    message: "New password and confirmation do not match.",
    path: ["confirmPassword"],
  });

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const validationResult = passwordSchema.safeParse({ oldPassword, newPassword, confirmPassword });
    
    if (!validationResult.success) {
      toast.error(validationResult.error.errors[0].message);
      return;
    }

    setIsChanging(true);
    try {
      const res = await changePassword(oldPassword, newPassword);
      if (res.success) {
        toast.success("Password updated successfully!");
        setOldPassword("");
        setNewPassword("");
        setConfirmPassword("");
      } else {
        toast.error(res.error || "Failed to change password.");
      }
    } catch (err: unknown) {
      const error = err as Error;
      toast.error(error.message || "An unexpected error occurred.");
    } finally {
      setIsChanging(false);
    }
  };

  return (
    <AppLayout>
      <div className="page-container animate-fade-in max-w-2xl mx-auto space-y-8">
        {/* Title Block */}
        <section className="mb-4">
          <p className="text-sm font-mono text-muted-foreground uppercase tracking-wider">
            Workspace Configuration
          </p>
          <h2 className="text-3xl font-display font-bold text-foreground mt-1">
            Account Settings
          </h2>
        </section>

        {/* Profile Card */}
        {user && (
          <section className="bg-card border border-border/80 rounded-xl p-6 space-y-4 shadow-sm">
            <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <UserIcon className="w-4 h-4 text-primary" /> Profile Info
            </h3>
            <div className="flex items-center gap-4 pt-2">
              <div className="w-14 h-14 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center text-lg font-bold font-mono text-primary uppercase shrink-0">
                {user.username.charAt(0)}
              </div>
              <div className="min-w-0 flex-1 space-y-1">
                <p className="text-base font-semibold text-foreground truncate">{user.username}</p>
                <p className="text-xs text-muted-foreground truncate">{user.email}</p>
              </div>
              <div className="shrink-0">
                <span className={cn(
                  "text-[10px] font-mono font-bold px-2.5 py-1 rounded-full border",
                  isAdmin
                    ? "bg-primary/10 border-primary/25 text-primary"
                    : "bg-muted border-border text-muted-foreground"
                )}>
                  {user.role.toUpperCase()}
                </span>
              </div>
            </div>
          </section>
        )}

        {/* Client & White-Label PDF Branding */}
        {activeWorkspace && (
          <section className="bg-card border border-border/80 rounded-xl p-6 space-y-4 shadow-sm">
            <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <Building2 className="w-4 h-4 text-primary" /> Active Client & White-Label Branding
            </h3>

            <form onSubmit={handleBrandingSubmit} className="space-y-4 pt-2">
              <div className="space-y-1.5">
                <Label htmlFor="active-client-name">Client Name</Label>
                <Input
                  id="active-client-name"
                  value={clientName}
                  onChange={(e) => setClientName(e.target.value)}
                  placeholder="e.g. Apex Traders Pvt Ltd"
                  className="bg-muted/20 border-border"
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="active-firm-name">CA Firm Header Name (White-Label PDF Header)</Label>
                <Input
                  id="active-firm-name"
                  value={firmName}
                  onChange={(e) => setFirmName(e.target.value)}
                  placeholder="e.g. Sharma & Associates CA Firm"
                  className="bg-muted/20 border-border"
                />
                <p className="text-xs text-muted-foreground">
                  When set, exported PDF audit reports for this client will be white-labeled with your firm's header name.
                </p>
              </div>

              <Button
                type="submit"
                disabled={isSavingBranding}
                className="bg-primary text-primary-foreground hover:bg-primary/95 font-medium shadow-sm"
              >
                {isSavingBranding ? "Saving Branding..." : "Save Branding"}
              </Button>
            </form>
          </section>
        )}

        {/* Appearance Toggle */}
        <section className="bg-card border border-border/80 rounded-xl p-6 space-y-4 shadow-sm">
          <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider flex items-center gap-2">
            {theme === "dark" ? <Moon className="w-4 h-4 text-primary" /> : <Sun className="w-4 h-4 text-primary" />}
            Appearance
          </h3>
          <div className="flex items-center justify-between pt-2">
            <div>
              <p className="text-sm font-medium text-foreground">Dark Theme</p>
              <p className="text-xs text-muted-foreground">Toggle application theme style dynamically</p>
            </div>
            <Switch
              checked={theme === "dark"}
              onCheckedChange={toggleTheme}
            />
          </div>
        </section>

        {/* Change Password Form */}
        <section className="bg-card border border-border/80 rounded-xl p-6 space-y-4 shadow-sm">
          <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider flex items-center gap-2">
            <Key className="w-4 h-4 text-primary" /> Update Password
          </h3>
          
          <form onSubmit={handlePasswordSubmit} className="space-y-4 pt-2">
            <div className="space-y-1.5">
              <Label htmlFor="old-password">Current Password</Label>
              <Input
                id="old-password"
                type="password"
                placeholder="Enter current password"
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
                className="bg-muted/20 border-border"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="new-password">New Password</Label>
              <Input
                id="new-password"
                type="password"
                placeholder="Enter new password (min. 8 characters)"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="bg-muted/20 border-border"
              />
              
              {/* Strength Indicator */}
              {newPassword && (
                <div className="space-y-1 pt-1 animate-fade-in">
                  <div className="flex items-center justify-between text-[10px] font-mono text-muted-foreground">
                    <span>Strength: <strong className="text-foreground">{strength.label}</strong></span>
                  </div>
                  <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                    <div className={cn("h-full transition-all duration-300", strength.color, strength.progress)} />
                  </div>
                </div>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="confirm-password">Confirm New Password</Label>
              <Input
                id="confirm-password"
                type="password"
                placeholder="Retype new password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="bg-muted/20 border-border"
              />
            </div>

            <Button
              type="submit"
              disabled={isChanging}
              className="bg-primary text-primary-foreground hover:bg-primary/95 font-medium shadow-sm"
            >
              {isChanging ? "Updating Password..." : "Update Password"}
            </Button>
          </form>
        </section>

        {/* Admin Tools Portal */}
        {isAdmin && (
          <section className="bg-primary/5 border border-primary/20 rounded-xl p-6 space-y-4 shadow-sm animate-fade-in">
            <h3 className="text-xs font-mono text-primary uppercase tracking-wider flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-primary" /> Administrator Portal
            </h3>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pt-2">
              <div>
                <p className="text-sm font-medium text-foreground">User Management Tools</p>
                <p className="text-xs text-muted-foreground">Reset passwords, manage platforms and delete runs recursively</p>
              </div>
              <Button
                variant="outline"
                className="border-primary/20 hover:bg-primary/10 text-primary shrink-0 self-start sm:self-auto"
                onClick={() => navigate("/admin")}
              >
                Open Admin Dashboard
              </Button>
            </div>
          </section>
        )}

        {/* Application Metadata & Sign Out */}
        <section className="pt-6 border-t border-border flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 font-sans text-xs text-muted-foreground">
          <div className="space-y-1">
            <p>Version: <span className="font-mono text-foreground">{APP_VERSION}</span></p>
            <p>Environment: <span className="font-mono text-foreground capitalize">{ENVIRONMENT}</span></p>
          </div>
          <Button
            variant="outline"
            onClick={handleLogout}
            className="text-destructive hover:text-destructive hover:bg-destructive/10 border-destructive/30 self-start sm:self-auto shrink-0"
          >
            <LogOut className="w-4 h-4 mr-2" />
            Sign Out of Workspace
          </Button>
        </section>
      </div>
    </AppLayout>
  );
}
