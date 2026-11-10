/**
 * TanStack Query hooks for Authentication domain.
 */

import { useQuery } from "@tanstack/react-query";
import { getMe } from "./requests";

export const authKeys = {
  all: ["v1", "auth"] as const,
  me: () => [...authKeys.all, "me"] as const,
};

export function useMeQuery(enabled = true) {
  return useQuery({
    queryKey: authKeys.me(),
    queryFn: ({ signal }) => getMe({ signal }),
    enabled,
    retry: 0,
    staleTime: 5 * 60 * 1000,
  });
}
