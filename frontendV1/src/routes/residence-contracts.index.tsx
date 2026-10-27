import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { AccessDenied } from "@/components/admin/access-denied";
import { ResidenceContractsPage } from "@/features/residence-contracts/residence-contracts-page";
import type { ResidenceContractStatus } from "@/features/residence-contracts/types";
import { useRbac } from "@/rbac/context";

const searchSchema = z.object({
  q: z.string().catch(""),
  status: z
    .enum(["draft", "pending_signature", "active", "cancelled"])
    .optional()
    .catch(undefined),
  page: z.coerce.number().int().min(1).catch(1),
  pageSize: z.coerce
    .number()
    .int()
    .refine((value) => [10, 20, 50].includes(value))
    .catch(10),
});

export const Route = createFileRoute("/residence-contracts/")({
  validateSearch: (search) => searchSchema.parse(search),
  component: ResidenceContractsIndex,
});

function ResidenceContractsIndex() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  const { can } = useRbac();
  if (!can("ktx.contracts.view")) return <AccessDenied />;

  return (
    <ResidenceContractsPage
      search={{
        q: search.q,
        status: search.status as ResidenceContractStatus | undefined,
        page: search.page,
        pageSize: search.pageSize,
      }}
      onSearch={(changes) =>
        void navigate({ search: (previous) => ({ ...previous, ...changes }) })
      }
      canCreate={can("ktx.contracts.create")}
      canUpdate={can("ktx.contracts.update")}
      onView={(contract) =>
        void navigate({
          to: "/residence-contracts/$contractId",
          params: { contractId: contract.id },
        })
      }
    />
  );
}
