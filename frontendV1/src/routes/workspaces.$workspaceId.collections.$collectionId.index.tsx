import { createFileRoute, redirect } from "@tanstack/react-router";
import { z } from "zod";
import { pageSearchSchema } from "@/features/workspaces/search";

const collectionDetailSearchSchema = pageSearchSchema.extend({
  sourceAction: z.enum(["ocr"]).optional(),
  stage: z
    .enum(["files", "ocr", "compiler", "publication", "serving"])
    .optional()
    .catch("files"),
  tab: z
    .enum(["sources", "compilations", "documents", "index"])
    .optional()
    .catch("sources"),
});

export const Route = createFileRoute(
  "/workspaces/$workspaceId/collections/$collectionId/",
)({
  validateSearch: (search) => collectionDetailSearchSchema.parse(search),
  beforeLoad: ({ params, search }) => {
    const stageMap: Record<
      string,
      "files" | "ocr" | "compiler" | "publication" | "serving"
    > = {
      sources: "files",
      compilations: "compiler",
      documents: "publication",
      index: "serving",
    };
    const stage =
      search.sourceAction === "ocr"
        ? "ocr"
        : (search.stage ??
          (search.tab ? (stageMap[search.tab] ?? "files") : "files"));

    throw redirect({
      to: "/workspaces/$workspaceId/knowledge/$knowledgeId",
      params: {
        workspaceId: params.workspaceId,
        knowledgeId: params.collectionId,
      },
      search: {
        page: search.page ?? 1,
        pageSize: search.pageSize ?? 20,
        stage,
        sourceAction: search.sourceAction,
      },
    });
  },
});
