import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";

import * as serviceA from "@/api/serviceA";

export type UserRole = "admin" | "user";

interface User {
  email: string;
  role: UserRole;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const logout = useCallback(() => {
    setUser(null);
    sessionStorage.removeItem("kaizen_user");
  }, []);

  useEffect(() => {
    let cancelled = false;

    // On initial load, verify server-side session via /api/auth/me/.
    // sessionStorage is only a UI cache; it is NOT the source of truth.
    (async () => {
      try {
        const me = await serviceA.getCurrentUser();
        if (cancelled) return;
        const userData: User = {
          email: me.email,
          role: me.is_staff ? "admin" : "user",
        };
        setUser(userData);
        sessionStorage.setItem("kaizen_user", JSON.stringify(userData));
      } catch {
        if (cancelled) return;
        setUser(null);
        sessionStorage.removeItem("kaizen_user");
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const login = async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    setIsLoading(true);
    try {
      const result = await serviceA.login(email, password);
      const me = result.user;
      const userData: User = {
        email: me.email,
        role: me.is_staff ? "admin" : "user",
      };
      setUser(userData);
      sessionStorage.setItem("kaizen_user", JSON.stringify(userData));
      setIsLoading(false);
      return { success: true };
    } catch (e) {
      setIsLoading(false);
      const err = e as { status?: number; bodyText?: string };
      if (err?.status === 401) return { success: false, error: "Invalid credentials." };
      if (err?.status === 400) return { success: false, error: "Email and password are required." };
      if (err?.status === 403) return { success: false, error: "Not authorized." };
      return { success: false, error: "Authentication failed." };
    }
  };

  const logoutServer = useCallback(async () => {
    try {
      await serviceA.logout();
    } finally {
      logout();
    }
  }, [logout]);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isAdmin: user?.role === "admin",
        login,
        logout: logoutServer,
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
