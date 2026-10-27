import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { z } from "zod";
import {
  RegistrationPeriodsPage,
  type RegistrationPeriodsSearch,
} from "@/features/registration-periods/registration-periods-page";

const searchSchema = z.object({
  q: z.string().catch(""),
  status: z
    .enum(["draft", "open", "closed", "archived"])
    .optional()
    .catch(undefined),
  page: z.coerce.number().int().min(1).catch(1),
  pageSize: z.coerce
    .number()
    .int()
    .refine((value) => [10, 20, 50].includes(value))
    .catch(10),
});

export const Route = createFileRoute("/registration-periods/")({
  validateSearch: (search) => searchSchema.parse(search),
  component: RegistrationPeriodsRoute,
});

function RegistrationPeriodsRoute() {
  const search = Route.useSearch();
  const navigate = useNavigate({ from: "/registration-periods/" });
  return (
    <RegistrationPeriodsPage
      search={search}
      onSearchChange={(changes: Partial<RegistrationPeriodsSearch>) =>
        void navigate({ search: (previous) => ({ ...previous, ...changes }) })
      }
    />
  );
}
