import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import type { AssistantSubView } from "@/components/assistants/assistant-workspace-nav";
import { AssistantDetailPage } from "@/features/assistants/assistant-detail-page";

const searchSchema = z.object({
  tab: z
    .enum([
      "overview",
      "models",
      "tools",
      "playground",
      "workflow",
      "channels",
      "quality",
      "runs",
    ])
    .optional(),
});

export const Route = createFileRoute("/assistants/$assistantId")({
  validateSearch: (search) => searchSchema.parse(search),
  component: AssistantDetailRoute,
});

function AssistantDetailRoute() {
  const { assistantId } = Route.useParams();
  const { tab } = Route.useSearch();
  return (
    <AssistantDetailPage
      assistantId={assistantId}
      initialTab={tab as AssistantSubView | undefined}
    />
  );
}
