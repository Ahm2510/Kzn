import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";
import { authApi, DjangoUser, setCsrfToken, clearCsrfToken, passwordApi } from "@/lib/api";

export type UserRole = "admin" | "user";

interface User {
  id: number;
  email: string;
  username: string;
  role: UserRole;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
  changePassword: (oldPw: string, newPw: string) => Promise<{ success: boolean; error?: string }>;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

function toUser(u: DjangoUser): User {
  return {
    id: u.id,
    email: u.email,
    username: u.username,
    role: u.is_staff ? "admin" : "user",
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // On mount, check if we have an active session
  useEffect(() => {
    authApi
      .me()
      .then(({ user: u }) => setUser(toUser(u)))
      .catch(() => setUser(null))
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(
    async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
      setIsLoading(true);
      try {
        const res = await authApi.login(email, password);
        setCsrfToken(res.csrfToken);
        setUser(toUser(res.user));
        return { success: true };
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Authentication failed.";
        return { success: false, error: message };
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // ignore
    }
    clearCsrfToken();
    setUser(null);
  }, []);

  const changePassword = useCallback(async (oldPw: string, newPw: string) => {
    try {
      await passwordApi.changePassword({ old_password: oldPw, new_password: newPw });
      return { success: true };
    } catch (err: unknown) {
      return { success: false, error: err instanceof Error ? err.message : "Password change failed." };
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isAdmin: user?.role === "admin",
        login,
        logout,
        changePassword,
        isLoading,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
