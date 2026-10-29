import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { KnowledgeDetailPage } from "@/features/knowledge/knowledge-detail-page";
import { pageSearchSchema } from "@/features/workspaces/search";

const ocrSearchSchema = pageSearchSchema.extend({
  sourceId: z.string().optional(),
  sourceAction: z.enum(["ocr"]).optional(),
});

export const Route = createFileRoute(
  "/workspaces/$workspaceId/knowledge/$knowledgeId/ocr",
)({
  validateSearch: (search) => ocrSearchSchema.parse(search),
  component: KnowledgeOcrRoute,
});

function KnowledgeOcrRoute() {
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
      activeStage="ocr"
      selectedSourceId={search.sourceId}
      onPageChange={(page) =>
        void navigate({ search: (previous) => ({ ...previous, page }) })
      }
      onPageSizeChange={(pageSize) =>
        void navigate({
          search: (previous) => ({ ...previous, pageSize, page: 1 }),
        })
      }
      onStageChange={(stage) => {
        if (stage === "files") {
          void navigate({
            to: "/workspaces/$workspaceId/knowledge/$knowledgeId",
            params: { workspaceId, knowledgeId },
            search: { page: 1, pageSize: 20 },
          });
        } else if (stage === "ocr") {
          void navigate({
            to: "/workspaces/$workspaceId/knowledge/$knowledgeId/ocr",
            params: { workspaceId, knowledgeId },
            search: { page: 1, pageSize: 20 },
          });
        } else {
          void navigate({
            to: "/workspaces/$workspaceId/knowledge/$knowledgeId",
            params: { workspaceId, knowledgeId },
            search: { page: 1, pageSize: 20, stage },
          });
        }
      }}
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
