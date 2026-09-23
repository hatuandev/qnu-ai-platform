import { useQuery } from "@tanstack/react-query";
import type { CurrentUser } from "@/app/auth/types";
import { getAuthStatus } from "@/services/auth-api";

export const currentUserQueryKey = ["auth", "current-user"] as const;

async function fetchCurrentUser(): Promise<CurrentUser | null> {
  const status = await getAuthStatus();
  if (!status.authenticated || !status.actor) {
    return null;
  }

  return {
    sub: status.actor.username,
    email: `${status.actor.username}@qnu.edu.vn`,
    name: status.actor.username || "Cán bộ Quản trị QNU",
    userType: status.actor.role || "admin",
    roles: [status.actor.role || "admin"],
    permissions: ["*"],
    roleMetadata: [],
  };
}

export function useCurrentUser(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: currentUserQueryKey,
    queryFn: fetchCurrentUser,
    staleTime: 5 * 60 * 1000,
    retry: false,
    refetchOnWindowFocus: false,
    enabled: options?.enabled ?? true,
  });
}

export { fetchCurrentUser };
