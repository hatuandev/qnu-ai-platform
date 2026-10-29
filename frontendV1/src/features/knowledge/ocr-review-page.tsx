import type { OcrSubTab } from "@/features/knowledge/ocr-tab-container";
import { SourceDetailPage } from "@/features/knowledge/source-detail-page";

export interface OcrReviewSearchParams {
  revisionId?: string;
  runId?: string;
  checkId?: string;
  page?: number;
  subTab?: OcrSubTab;
}

export function OcrReviewPage({
  workspaceId,
  collectionId,
  sourceId,
  search,
  onSearchChange,
}: {
  workspaceId: string;
  collectionId: string;
  sourceId: string;
  search?: OcrReviewSearchParams;
  onSearchChange?: (params: Partial<OcrReviewSearchParams>) => void;
}) {
  return (
    <SourceDetailPage
      workspaceId={workspaceId}
      collectionId={collectionId}
      sourceId={sourceId}
      search={search}
      onSearchChange={onSearchChange}
    />
  );
}
