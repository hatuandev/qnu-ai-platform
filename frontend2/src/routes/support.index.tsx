import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { z } from "zod";
import {
  SupportPage,
  type SupportSearch,
  supportRequestTypes,
  supportStatuses,
} from "@/features/support/support-page";

const searchSchema = z.object({
  q: z.union([z.string(), z.number()]).catch(""),
  status: z.enum(supportStatuses).optional().catch(undefined),
  type: z.enum(supportRequestTypes).optional().catch(undefined),
  page: z.coerce.number().int().min(1).catch(1),
  pageSize: z.coerce
    .number()
    .int()
    .refine((value) => [10, 20, 50].includes(value))
    .catch(10),
});

export const Route = createFileRoute("/support/")({
  validateSearch: (search) => searchSchema.parse(search),
  component: SupportRoute,
});

function SupportRoute() {
  const search = Route.useSearch();
  const navigate = useNavigate({ from: "/support/" });
  return (
    <SupportPage
      search={search}
      onSearchChange={(changes: Partial<SupportSearch>) =>
        void navigate({ search: (previous) => ({ ...previous, ...changes }) })
      }
    />
  );
}
