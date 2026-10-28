import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { FeatureEntryPage } from "@/features/workspaces/feature-entry-page";
import { isWorkspaceFeature } from "@/navigation/workspace-features";

const searchSchema = z.object({
  workspaceId: z.string().min(1).max(64).optional(),
  page: z.coerce.number().int().min(1).catch(1),
});
export const Route = createFileRoute("/workspaces/choose/$feature")({
  validateSearch: (search) => searchSchema.parse(search),
  component: ChooseDestination,
});
function ChooseDestination() {
  const { feature } = Route.useParams();
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  if (!isWorkspaceFeature(feature))
    return <p role="alert">Không tìm thấy chức năng.</p>;
  return (
    <FeatureEntryPage
      key={feature}
      feature={feature}
      {...search}
      onPageChange={(page) =>
        void navigate({ search: (previous) => ({ ...previous, page }) })
      }
    />
  );
}
