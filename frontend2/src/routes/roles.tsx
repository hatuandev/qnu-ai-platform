import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { z } from "zod";
import { RolesPage, type RolesSearch } from "@/features/roles/roles-page";

const searchSchema = z.object({
  q: z.string().catch(""),
  create: z.coerce.boolean().catch(false),
  type: z.union([z.literal(""), z.enum(["system", "custom"])]).catch(""),
  status: z.union([z.literal(""), z.enum(["active", "inactive"])]).catch(""),
  page: z.coerce.number().int().min(1).catch(1),
  pageSize: z.coerce
    .number()
    .int()
    .refine((value) => [10, 20, 50].includes(value))
    .catch(10),
  sort: z
    .enum([
      "name.asc",
      "name.desc",
      "userCount.asc",
      "userCount.desc",
      "permissions.asc",
      "permissions.desc",
      "status.asc",
      "status.desc",
    ])
    .catch("name.asc"),
});

export const Route = createFileRoute("/roles")({
  validateSearch: (search) => searchSchema.parse(search),
  component: RolesRoute,
});

function RolesRoute() {
  const search = Route.useSearch();
  const navigate = useNavigate({ from: "/roles" });
  return (
    <RolesPage
      search={search}
      onSearchChange={(changes: Partial<RolesSearch>) =>
        void navigate({ search: (previous) => ({ ...previous, ...changes }) })
      }
    />
  );
}
