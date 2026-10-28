import { createFileRoute } from "@tanstack/react-router";
import { ProvidersPage } from "@/features/modelops/providers-page";

export const Route = createFileRoute("/providers/")({
  component: ProvidersIndex,
});

function ProvidersIndex() {
  const navigate = Route.useNavigate();

  return (
    <ProvidersPage
      onOpenProvider={(provider) =>
        void navigate({
          to: "/providers/$providerId",
          params: { providerId: provider.id },
        })
      }
    />
  );
}

