import { createFileRoute } from "@tanstack/react-router";
import type { z } from "zod";
import {
  DifficultAreasPage,
  difficultAreasSearchSchema,
} from "@/features/difficult-areas/difficult-areas-page";

export const Route = createFileRoute("/difficult-areas/")({
  validateSearch: (search) => difficultAreasSearchSchema.parse(search),
  component: DifficultAreasRoute,
});

function DifficultAreasRoute() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  return (
    <DifficultAreasPage
      search={search}
      updateSearch={(
        changes: Partial<z.infer<typeof difficultAreasSearchSchema>>,
      ) =>
        void navigate({ search: (previous) => ({ ...previous, ...changes }) })
      }
    />
  );
}
