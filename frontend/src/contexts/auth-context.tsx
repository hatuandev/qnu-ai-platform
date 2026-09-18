import { getAuthStatus, loginWithPassword, logout as logoutApi } from "@/services/auth-api";
import type { AuthActor } from "@/types/auth";
import { type ReactNode, createContext, useCallback, useContext, useEffect, useState } from "react";

interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  actor: AuthActor | null;
  login: (password: string) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [actor, setActor] = useState<AuthActor | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const checkAuth = useCallback(async () => {
    try {
      setIsLoading(true);
      const res = await getAuthStatus();
      if (res.authenticated) {
        setIsAuthenticated(true);
        setActor(res.actor || null);
      } else {
        setIsAuthenticated(false);
        setActor(null);
      }
    } catch {
      setIsAuthenticated(false);
      setActor(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = useCallback(async (password: string) => {
    const res = await loginWithPassword(password);
    if (res.authenticated) {
      setIsAuthenticated(true);
      setActor(res.actor || null);
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutApi();
    } finally {
      setIsAuthenticated(false);
      setActor(null);
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        isLoading,
        actor,
        login,
        logout,
        checkAuth,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
