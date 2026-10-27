import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { z } from "zod";
import { userSortValues } from "@/features/users/types";
import { UsersPage, type UsersSearch } from "@/features/users/users-page";

function sanitizeFacetParam(value: string) {
  return [
    ...new Set(
      value
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    ),
  ].join(",");
}

const searchSchema = z.object({
  q: z.string().catch(""),
  create: z.coerce.boolean().catch(false),
  roles: z.string().catch("").transform(sanitizeFacetParam),
  statuses: z
    .string()
    .catch("")
    .transform((value) => sanitizeFacetParam(value)),
  page: z.coerce.number().int().min(1).catch(1),
  pageSize: z.coerce
    .number()
    .int()
    .refine((value) => [10, 20, 50].includes(value))
    .catch(10),
  sort: z.enum(userSortValues).catch("createdAt.desc"),
});

export const Route = createFileRoute("/users/")({
  validateSearch: (search) => searchSchema.parse(search),
  component: UsersRoute,
});

function UsersRoute() {
  const search = Route.useSearch();
  const navigate = useNavigate({ from: "/users/" });
  return (
    <UsersPage
      search={search}
      onSearchChange={(changes: Partial<UsersSearch>) =>
        void navigate({ search: (previous) => ({ ...previous, ...changes }) })
      }
    />
  );
}
