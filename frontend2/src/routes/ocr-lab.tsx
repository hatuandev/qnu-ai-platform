import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { ScanStudioPage } from "@/features/knowledge/scan-studio-page";

const searchSchema = z.object({
  docId: z.string().optional(),
  documentId: z.string().optional(),
  collectionId: z.string().optional(),
});

export const Route = createFileRoute("/ocr-lab")({
  validateSearch: (search) => searchSchema.parse(search),
  component: OcrLabRoute,
});

function OcrLabRoute() {
  const search = Route.useSearch();
  const docId = search.docId || search.documentId;
  const collectionId = search.collectionId;

  return (
    <ScanStudioPage documentId={docId} collectionId={collectionId} />
  );
}
