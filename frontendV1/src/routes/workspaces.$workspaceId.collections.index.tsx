import { createFileRoute, redirect } from "@tanstack/react-router";
import { pageSearchSchema } from "@/features/workspaces/search";

export const Route = createFileRoute("/workspaces/$workspaceId/collections/")({
  validateSearch: (search) => pageSearchSchema.parse(search),
  beforeLoad: ({ params, search }) => {
    throw redirect({
      to: "/workspaces/$workspaceId/knowledge",
      params: { workspaceId: params.workspaceId },
      search: { page: search.page ?? 1, pageSize: search.pageSize ?? 20 },
    });
  },
});
