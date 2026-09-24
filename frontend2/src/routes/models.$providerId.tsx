import { createFileRoute } from "@tanstack/react-router";
import { ProviderDetailPage } from "@/features/modelops/provider-detail-page";

export const Route = createFileRoute("/models/$providerId")({
  component: ProviderDetailRoute,
});

function ProviderDetailRoute() {
  const { providerId } = Route.useParams();
  return <ProviderDetailPage providerId={providerId} />;
}
