import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import {
  KnowledgeDetailPage,
  type KnowledgeStage,
} from "@/features/knowledge/knowledge-detail-page";
import { pageSearchSchema } from "@/features/workspaces/search";

const knowledgeDetailSearchSchema = pageSearchSchema.extend({
  stage: z
    .enum(["files", "ocr", "compiler", "publication", "serving"])
    .optional()
    .catch("files"),
  sourceId: z.string().optional(),
  sourceAction: z.enum(["ocr"]).optional(),
  tab: z.string().optional(),
});

export const Route = createFileRoute(
  "/workspaces/$workspaceId/knowledge/$knowledgeId/",
)({
  validateSearch: (search) => knowledgeDetailSearchSchema.parse(search),
  component: KnowledgeDetailRoute,
});

function KnowledgeDetailRoute() {
  const { workspaceId, knowledgeId } = Route.useParams();
  const search = Route.useSearch();
  const navigate = Route.useNavigate();

  return (
    <KnowledgeDetailPage
      key={`${workspaceId}:${knowledgeId}`}
      workspaceId={workspaceId}
      knowledgeId={knowledgeId}
      page={search.page}
      pageSize={search.pageSize}
      activeStage={(search.stage as KnowledgeStage) ?? "files"}
      selectedSourceId={search.sourceId}
      onPageChange={(page) =>
        void navigate({ search: (previous) => ({ ...previous, page }) })
      }
      onPageSizeChange={(pageSize) =>
        void navigate({
          search: (previous) => ({ ...previous, pageSize, page: 1 }),
        })
      }
      onStageChange={(stage) =>
        void navigate({
          search: (previous) => ({ ...previous, stage, page: 1 }),
        })
      }
      onSelectSourceId={(sourceId) =>
        void navigate({
          search: (previous) => ({
            ...previous,
            sourceId: sourceId ?? undefined,
          }),
        })
      }
    />
  );
}
