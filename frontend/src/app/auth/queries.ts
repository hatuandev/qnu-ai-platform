import { useQuery } from "@tanstack/react-query";
import type { CurrentUser } from "@/app/auth/types";
import { getAuthStatus } from "@/services/auth-api";

export const currentUserQueryKey = ["auth", "current-user"] as const;

import { getStoredOidcUser } from "@/app/auth/oidc";

async function fetchCurrentUser(): Promise<CurrentUser | null> {
  // 1. Ưu tiên kiểm tra phiên đăng nhập từ QNU Single Sign-On (OpenIddict)
  const oidcUser = await getStoredOidcUser();
  if (oidcUser) {
    return oidcUser;
  }

  // 2. Fallback: Kiểm tra phiên Dev Access Gate từ Backend API
  const status = await getAuthStatus();
  if (!status.authenticated || !status.actor) {
    return null;
  }

  return {
    sub: status.actor.username,
    email: `${status.actor.username}@qnu.edu.vn`,
    name:
      status.actor.display_name ||
      status.actor.username ||
      "Cán bộ Quản trị QNU",
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
