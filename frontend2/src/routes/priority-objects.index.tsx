import { createFileRoute } from "@tanstack/react-router";
import type { z } from "zod";
import {
  PriorityObjectsPage,
  priorityObjectsSearchSchema,
} from "@/features/priority-objects/priority-objects-page";

export const Route = createFileRoute("/priority-objects/")({
  validateSearch: (search) => priorityObjectsSearchSchema.parse(search),
  component: PriorityObjectsRoute,
});

function PriorityObjectsRoute() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  return (
    <PriorityObjectsPage
      search={search}
      updateSearch={(
        changes: Partial<z.infer<typeof priorityObjectsSearchSchema>>,
      ) =>
        void navigate({ search: (previous) => ({ ...previous, ...changes }) })
      }
    />
  );
}
