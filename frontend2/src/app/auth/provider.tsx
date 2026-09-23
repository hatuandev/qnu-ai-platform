import { useQueryClient } from "@tanstack/react-query";
import { createContext, type ReactNode, useContext } from "react";
import { currentUserQueryKey, useCurrentUser } from "@/app/auth/queries";
import type { CurrentUser } from "@/app/auth/types";
import { loginWithPassword, logout as logoutApi } from "@/services/auth-api";

type AuthContextValue = {
  user: CurrentUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
  login: (password: string) => Promise<void>;
  signIn: (returnUrl?: string) => void;
  signOut: (returnUrl?: string) => Promise<void>;
  isDemoMode: boolean;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const query = useCurrentUser();
  const user = query.data ?? null;

  const login = async (password: string) => {
    const res = await loginWithPassword(password);
    if (res.authenticated && res.actor) {
      const actor = res.actor;
      const currentUser: CurrentUser = {
        sub: actor.username,
        email: `${actor.username}@qnu.edu.vn`,
        name: actor.display_name || actor.username || "Cán bộ Quản trị QNU",
        userType: actor.role || "admin",
        roles: [actor.role || "admin"],
        permissions: ["*"],
        roleMetadata: [],
      };
      queryClient.setQueryData(currentUserQueryKey, currentUser);
    }
    await queryClient.invalidateQueries({ queryKey: currentUserQueryKey });
  };

  const signOut = async (_returnUrl?: string) => {
    try {
      await logoutApi();
    } finally {
      queryClient.setQueryData(currentUserQueryKey, null);
      window.location.href = "/sign-in";
    }
  };

  const signIn = (_returnUrl?: string) => {
    window.location.href = "/sign-in";
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: user !== null,
        isLoading: query.isLoading,
        error: !(query.error instanceof Error) ? null : query.error,
        refetch: () => void query.refetch(),
        login,
        signIn,
        signOut,
        isDemoMode: false,
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
