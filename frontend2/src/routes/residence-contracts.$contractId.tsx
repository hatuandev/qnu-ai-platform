import { createFileRoute } from "@tanstack/react-router";
import { AccessDenied } from "@/components/admin/access-denied";
import { ResidenceContractDetail } from "@/features/residence-contracts/residence-contract-detail";
import { useRbac } from "@/rbac/context";

export const Route = createFileRoute("/residence-contracts/$contractId")({
  component: ResidenceContractDetailRoute,
});

function ResidenceContractDetailRoute() {
  const { contractId } = Route.useParams();
  const { can } = useRbac();
  if (!can("ktx.contracts.view")) return <AccessDenied />;
  return <ResidenceContractDetail id={contractId} />;
}
