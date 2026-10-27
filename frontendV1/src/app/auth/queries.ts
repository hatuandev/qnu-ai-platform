import { useQuery } from "@tanstack/react-query";
import { backendFetch } from "@/app/api/backend-fetch";
import type { CurrentUser } from "@/app/auth/types";
import { runtimeConfig } from "@/app/config/runtime";

export const currentUserQueryKey = ["auth", "current-user"] as const;

async function fetchCurrentUser(): Promise<CurrentUser | null> {
  const baseUrl = runtimeConfig.bffBaseUrl.replace(/\/$/, "");
  const response = await backendFetch(`${baseUrl}/user`, {
    credentials: "include",
  });

  // Handle the unauthenticated probe before reading the response body. This
  // matches the legacy ClientApp flow and avoids waiting on a proxied 401
  // response body before the auth gate can redirect to /bff/login.
  if (response.status === 401) return null;
  if (!response.ok) throw new Error(`/bff/user returned ${response.status}`);

  const user = (await response.json()) as CurrentUser;
  return {
    ...user,
    roleMetadata: user.roleMetadata ?? [],
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
