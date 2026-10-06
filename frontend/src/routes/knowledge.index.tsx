import { createFileRoute } from "@tanstack/react-router";
import { KnowledgePage } from "@/features/knowledge/knowledge-page";

export const Route = createFileRoute("/knowledge/")({
  component: KnowledgeIndexRoute,
});

function KnowledgeIndexRoute() {
  return <KnowledgePage />;
}
