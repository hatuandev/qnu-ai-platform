import { createFileRoute } from "@tanstack/react-router";
import { ConnectionDetail } from "@/features/modelops/connections/connection-detail";
import { ProviderDetail } from "@/features/modelops/provider-detail";
import { useProviderQuery } from "@/features/modelops/queries";

export const Route = createFileRoute("/modelops/providers/$providerId")({
  component: ProviderOrConnection,
});

function ProviderOrConnection() {
  const { providerId } = Route.useParams();
  const query = useProviderQuery(providerId);
  return query.data?.is_connection ? (
    <ConnectionDetail connectionId={providerId} />
  ) : (
    <ProviderDetail providerId={providerId} />
  );
}
