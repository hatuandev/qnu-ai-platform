import { createContext, type ReactNode, useContext } from "react";
import { useCurrentUser } from "@/app/auth/queries";
import type { CurrentUser } from "@/app/auth/types";
import { runtimeConfig } from "@/app/config/runtime";

type AuthContextValue = {
  user: CurrentUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
  signIn: (returnUrl?: string) => void;
  signOut: (returnUrl?: string) => void;
  isDemoMode: boolean;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function getReturnUrl(returnUrl?: string): string {
  if (returnUrl?.startsWith("/") && !returnUrl.startsWith("//")) {
    return returnUrl;
  }
  return `${window.location.pathname}${window.location.search}`;
}

function navigateToBff(path: "login" | "logout", returnUrl?: string): void {
  const target = `${runtimeConfig.bffBaseUrl}/${path}?returnUrl=${encodeURIComponent(
    getReturnUrl(returnUrl),
  )}`;
  if (path === "login") {
    window.location.replace(target);
    return;
  }

  window.location.assign(target);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const isDemoMode = runtimeConfig.authMode === "demo";
  const query = useCurrentUser({ enabled: !isDemoMode });
  const user = query.data ?? null;

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: isDemoMode || user !== null,
        isLoading: isDemoMode ? false : query.isLoading,
        error:
          isDemoMode || !(query.error instanceof Error) ? null : query.error,
        refetch: () => void query.refetch(),
        signIn: (returnUrl) => {
          if (!isDemoMode) navigateToBff("login", returnUrl);
        },
        signOut: (returnUrl) => {
          if (!isDemoMode) navigateToBff("logout", returnUrl);
        },
        isDemoMode,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used within AuthProvider");
  return value;
}
