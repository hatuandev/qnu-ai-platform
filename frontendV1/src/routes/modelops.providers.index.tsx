import { createFileRoute } from "@tanstack/react-router";
import { ProvidersPage } from "@/features/modelops/providers-page";

export const Route = createFileRoute("/modelops/providers/")({
  component: ProvidersIndex,
});

function ProvidersIndex() {
  const navigate = Route.useNavigate();

  return (
    <ProvidersPage
      onOpenProvider={(provider) =>
        void navigate({
          to: "/modelops/providers/$providerId",
          params: { providerId: provider.id },
        })
      }
    />
  );
}
