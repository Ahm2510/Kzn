import { useState } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { passwordApi, analysisApi, AdminResetPasswordPayload } from "@/lib/api";
import { useAnalysisRuns } from "@/hooks/useAnalysis";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  ShieldAlert,
  UserCog,
  Key,
  Trash2,
  Database,
  RefreshCw,
  AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/hooks/useAuth";
import { Navigate } from "react-router-dom";

export default function Admin() {
  const { isAdmin, isLoading: loadingAuth } = useAuth();
  const qc = useQueryClient();

  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [showDeleteAllDialog, setShowDeleteAllDialog] = useState(false);
  const [isDeletingAll, setIsDeletingAll] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");

  // Queries
  const { data: users, refetch: refetchUsers, isLoading: loadingUsers } = useQuery({
    queryKey: ["admin-users"],
    queryFn: passwordApi.adminListUsers,
    enabled: !!isAdmin,
  });

  const { data: allRuns } = useAnalysisRuns();

  // Reset Password Mutation
  const resetPasswordMutation = useMutation({
    mutationFn: (payload: AdminResetPasswordPayload) => passwordApi.adminResetUserPassword(payload),
    onSuccess: () => {
      toast.success("User password has been reset successfully.");
      refetchUsers();
      setSelectedUserId(null);
      setNewPassword("");
    },
    onError: (err: Error) => {
      toast.error(err.message || "Failed to reset password.");
    },
  });

  // Handle Purge All Runs
  const handleDeleteAll = async () => {
    if (!allRuns || allRuns.length === 0) {
      toast.error("No analysis runs available to delete.");
      return;
    }
    setIsDeletingAll(true);
    try {
      await Promise.all(allRuns.map((run) => analysisApi.delete(run.id)));
      qc.invalidateQueries({ queryKey: ["analysis-runs"] });
      toast.success("Successfully deleted all analysis runs.");
    } catch (err: unknown) {
      const error = err as Error;
      toast.error(error.message || "Failed to delete all runs.");
    } finally {
      setIsDeletingAll(false);
      setShowDeleteAllDialog(false);
    }
  };

  const handleResetSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUserId || !newPassword) return;
    if (newPassword.length < 8) {
      toast.error("Password must be at least 8 characters long.");
      return;
    }
    resetPasswordMutation.mutate({
      user_id: selectedUserId,
      new_password: newPassword,
    });
  };

  // Guard routing
  if (loadingAuth) {
    return (
      <AppLayout>
        <div className="page-container flex items-center justify-center min-h-[50vh]">
          <div className="w-8 h-8 border-4 border-primary/20 border-t-primary rounded-full animate-spin" />
        </div>
      </AppLayout>
    );
  }

  if (!isAdmin) {
    toast.error("Admin access required.");
    return <Navigate to="/" replace />;
  }

  const selectedUser = users?.find((u) => u.id === selectedUserId);

  return (
    <AppLayout>
      <div className="page-container animate-fade-in max-w-5xl mx-auto space-y-8">
        {/* Title Block */}
        <section className="mb-4">
          <p className="text-sm font-mono text-primary uppercase tracking-wider">
            System Administration
          </p>
          <h2 className="text-3xl font-display font-bold text-foreground mt-1">
            Admin Panel
          </h2>
        </section>

        {/* System Stats Section */}
        <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-card border border-border rounded-xl p-5 shadow-sm space-y-1">
            <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <UserCog className="w-4 h-4 text-primary" /> Total Users
            </h3>
            <p className="text-3xl font-display font-bold text-foreground">
              {loadingUsers ? "-" : users?.length || 0}
            </p>
          </div>
          <div className="bg-card border border-border rounded-xl p-5 shadow-sm space-y-1">
            <h3 className="text-xs font-mono text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <Database className="w-4 h-4 text-primary" /> Total Analysis Runs
            </h3>
            <p className="text-3xl font-display font-bold text-foreground">
              {allRuns ? allRuns.length : 0}
            </p>
          </div>
        </section>

        {/* User Management Section */}
        <section className="bg-card border border-border rounded-xl p-6 space-y-6 shadow-sm">
          <div className="flex items-center justify-between border-b border-border/80 pb-4">
            <h3 className="text-sm font-mono text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <UserCog className="w-4 h-4 text-primary" /> User Management
            </h3>
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetchUsers()}
              className="h-8 px-3 border-border"
            >
              <RefreshCw className="w-3.5 h-3.5 mr-1.5" /> Refresh Users
            </Button>
          </div>

          {loadingUsers ? (
            <div className="py-8 space-y-3">
              <div className="h-8 bg-muted animate-pulse rounded" />
              <div className="h-10 bg-muted animate-pulse rounded" />
              <div className="h-10 bg-muted animate-pulse rounded" />
            </div>
          ) : !users || users.length === 0 ? (
            <p className="text-sm text-muted-foreground py-6 text-center">No users found.</p>
          ) : (
            <div className="rounded-lg border border-border overflow-hidden bg-card">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/40 hover:bg-muted/40 border-b border-border/80">
                    <TableHead className="text-xs font-mono font-bold text-muted-foreground pl-6">ID</TableHead>
                    <TableHead className="text-xs font-mono font-bold text-muted-foreground">Username</TableHead>
                    <TableHead className="text-xs font-mono font-bold text-muted-foreground">Email</TableHead>
                    <TableHead className="text-xs font-mono font-bold text-muted-foreground">Role</TableHead>
                    <TableHead className="text-xs font-mono font-bold text-muted-foreground">Last Login</TableHead>
                    <TableHead className="text-xs font-mono font-bold text-muted-foreground w-36 pr-6 text-right" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {users.map((u) => (
                    <TableRow key={u.id} className="border-b border-border/60 hover:bg-muted/10">
                      <TableCell className="font-mono text-sm pl-6">#{u.id}</TableCell>
                      <TableCell className="font-semibold text-foreground">{u.username}</TableCell>
                      <TableCell className="text-muted-foreground text-sm">{u.email}</TableCell>
                      <TableCell>
                        <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                          u.is_staff
                            ? "bg-primary/10 border-primary/25 text-primary"
                            : "bg-muted border-border text-muted-foreground"
                        }`}>
                          {u.is_staff ? "ADMIN" : "USER"}
                        </span>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground font-sans">
                        {u.last_login ? new Date(u.last_login).toLocaleString() : "Never"}
                      </TableCell>
                      <TableCell className="pr-6 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedUserId(u.id)}
                          className="h-8 px-2 hover:bg-primary/10 text-primary hover:text-primary font-medium"
                        >
                          <Key className="w-3.5 h-3.5 mr-1" /> Reset PW
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </section>

        {/* Destructive purges / Dangous actions */}
        <section className="bg-destructive/5 border border-destructive/20 rounded-xl p-6 space-y-6 shadow-sm">
          <div className="flex items-center gap-2 border-b border-destructive/15 pb-4">
            <ShieldAlert className="w-4 h-4 text-destructive" />
            <h3 className="text-sm font-mono text-destructive uppercase tracking-wider">
              Destructive System Actions
            </h3>
          </div>
          
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-foreground">Purge All Analysis Runs</p>
              <p className="text-xs text-muted-foreground font-sans mt-0.5 max-w-xl">
                This will delete every single analysis run and all related data recursively from the platform database caches. This action is irreversible.
              </p>
            </div>
            
            <Button
              variant="destructive"
              disabled={!allRuns || allRuns.length === 0}
              onClick={() => setShowDeleteAllDialog(true)}
              className="shrink-0 bg-destructive hover:bg-destructive/95 text-destructive-foreground shadow-sm"
            >
              <Trash2 className="w-4 h-4 mr-2" /> Purge All Runs ({allRuns?.length || 0})
            </Button>
          </div>
        </section>

        {/* Reset Password Dialog */}
        <Dialog open={selectedUserId !== null} onOpenChange={(open) => !open && setSelectedUserId(null)}>
          <DialogContent className="max-w-sm sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="text-lg font-display font-bold">Reset Password</DialogTitle>
              <DialogDescription className="font-sans text-xs">
                Forcing user password adjustment for user <strong>{selectedUser?.username}</strong>.
              </DialogDescription>
            </DialogHeader>

            <form onSubmit={handleResetSubmit} className="space-y-4 py-2">
              <div className="space-y-1.5">
                <Label htmlFor="admin-new-password">New Password</Label>
                <Input
                  id="admin-new-password"
                  type="password"
                  placeholder="Enter at least 8 characters"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="bg-muted/30 border-border"
                />
              </div>

              <DialogFooter className="pt-4 flex flex-col sm:flex-row gap-2 sm:justify-end">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setSelectedUserId(null)}
                  className="border-border text-foreground hover:bg-muted"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={resetPasswordMutation.isPending}
                  className="bg-primary text-primary-foreground hover:bg-primary/95"
                >
                  {resetPasswordMutation.isPending ? "Resetting..." : "Confirm Reset"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Purge Confirmation Alert Dialog */}
        <AlertDialog open={showDeleteAllDialog} onOpenChange={(open) => {
          setShowDeleteAllDialog(open);
          if (!open) setDeleteConfirmText("");
        }}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle className="text-destructive flex items-center gap-2">
                <AlertTriangle className="w-5 h-5" /> Dangerous System Action!
              </AlertDialogTitle>
              <AlertDialogDescription asChild>
                <div>
                  <p className="mb-4 text-sm text-muted-foreground">
                    Are you absolutely sure you want to delete **ALL {allRuns?.length || 0} analysis runs**? This will completely wipe all uploaded dataset pointers, calculated insights, scoring metrics, and PDF summaries from the platform database caches.
                  </p>
                  <div className="mt-4 space-y-2">
                    <Label htmlFor="confirm-delete" className="text-foreground">Type <strong>DELETE</strong> to confirm:</Label>
                    <Input
                      id="confirm-delete"
                      value={deleteConfirmText}
                      onChange={(e) => setDeleteConfirmText(e.target.value)}
                      placeholder="DELETE"
                      className="border-destructive/20 focus-visible:ring-destructive"
                    />
                  </div>
                </div>
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel Purge</AlertDialogCancel>
              <AlertDialogAction
                className="bg-destructive hover:bg-destructive/90 text-destructive-foreground"
                disabled={isDeletingAll || deleteConfirmText !== "DELETE"}
                onClick={handleDeleteAll}
              >
                {isDeletingAll ? "Purging Database..." : "Wipe All Databases"}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </AppLayout>
  );
}
