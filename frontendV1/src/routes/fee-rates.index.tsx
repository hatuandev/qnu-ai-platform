import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { z } from "zod";
import {
  FeeRatesPage,
  type FeeRatesSearch,
} from "@/features/fee-rates/fee-rates-page";

const searchSchema = z.object({
  q: z.string().catch(""),
  academicYearId: z.string().optional().catch(undefined),
  roomTypeId: z.string().optional().catch(undefined),
  buildingId: z.string().optional().catch(undefined),
  floorId: z.string().optional().catch(undefined),
  roomId: z.string().optional().catch(undefined),
  status: z.enum(["active", "inactive"]).optional().catch(undefined),
  page: z.coerce.number().int().min(1).catch(1),
  pageSize: z.coerce
    .number()
    .int()
    .refine((value) => [10, 20, 50].includes(value))
    .catch(10),
});

export const Route = createFileRoute("/fee-rates/")({
  validateSearch: (search) => searchSchema.parse(search),
  component: FeeRatesRoute,
});

function FeeRatesRoute() {
  const search = Route.useSearch();
  const navigate = useNavigate({ from: "/fee-rates/" });
  return (
    <FeeRatesPage
      search={search}
      onSearchChange={(changes: Partial<FeeRatesSearch>) =>
        void navigate({ search: (previous) => ({ ...previous, ...changes }) })
      }
    />
  );
}
