import { createFileRoute } from "@tanstack/react-router";
import { ProviderDetail } from "@/features/modelops/provider-detail";

export const Route = createFileRoute("/modelops/providers/$providerId")({
  component: () => <ProviderDetail providerId={Route.useParams().providerId} />,
});
