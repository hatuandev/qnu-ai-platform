import { useBlocker } from "@tanstack/react-router";
import {
  AlertCircle,
  Cpu,
  FileCheck2,
  ImageIcon,
  Layers,
  ListOrdered,
  Loader2,
  Play,
} from "lucide-react";
import { useCallback, useEffect, useId, useMemo, useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { OcrArtifactsPanel } from "@/features/knowledge/ocr-artifacts-panel";
import { OcrComparisonView } from "@/features/knowledge/ocr-comparison-view";
import {
  type OcrDraftScope,
  useOcrDraft,
} from "@/features/knowledge/ocr-draft-store";
import {
  useProcessingRunDetailQuery,
  useProcessingRunsQuery,
  useTextReviewQuery,
} from "@/features/knowledge/ocr-queries";
import { OcrRequestDialog } from "@/features/knowledge/ocr-request-dialog";
import { OcrRunsList } from "@/features/knowledge/ocr-runs-list";
import {
  formatOcrError,
  formatRunStatus,
  isDocx,
} from "@/features/knowledge/ocr-schemas";
import { OcrTextReviewPanel } from "@/features/knowledge/ocr-text-review-panel";
import type { ProcessingRunResponse } from "@/features/knowledge/ocr-types";

export type OcrSubTab = "runs" | "comparison" | "review" | "artifacts";

export function OcrTabContainer({
  workspaceId,
  collectionId,
  sourceId,
  revisionId,
  revisionNo,
  fileName,
  contentType,
  canManage,
  initialRunId,
  initialPage,
  initialSubTab,
  checkId,
  onDeepLinkChange,
}: {
  workspaceId: string;
  collectionId: string;
  sourceId: string;
  revisionId: string;
  revisionNo: number;
  fileName: string;
  contentType: string;
  canManage: boolean;
  initialRunId?: string;
  initialPage?: number;
  initialSubTab?: OcrSubTab;
  checkId?: string;
  onDeepLinkChange?: (params: {
    runId?: string;
    page?: number;
    subTab?: OcrSubTab;
    checkId?: string;
  }) => void;
}) {
  const [requestDialogOpen, setRequestDialogOpen] = useState(false);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(
    initialRunId ?? null,
  );
  const [activePage, setActivePage] = useState<number>(initialPage ?? 1);
  const [activeSubTab, setActiveSubTab] = useState<OcrSubTab>(
    initialSubTab ?? "runs",
  );
  const [runsListPage, setRunsListPage] = useState<number>(1);
  useEffect(() => {
    if (initialRunId) setSelectedRunId(initialRunId);
  }, [initialRunId]);
  useEffect(() => {
    if (initialSubTab) setActiveSubTab(initialSubTab);
  }, [initialSubTab]);

  // Load runs to default select the latest run if none is deep-linked
  const runsQuery = useProcessingRunsQuery(
    workspaceId,
    collectionId,
    sourceId,
    revisionId,
    1,
    10,
  );

  const runs = runsQuery.data?.items ?? [];

  // Auto-select latest run if not set
  useEffect(() => {
    if (!selectedRunId && runs.length > 0) {
      const latest = runs[0];
      setSelectedRunId(latest.id);
    }
  }, [selectedRunId, runs]);

  // Load detailed information for the active run
  const runDetailQuery = useProcessingRunDetailQuery(
    workspaceId,
    collectionId,
    sourceId,
    revisionId,
    selectedRunId,
  );

  const activeRun = runDetailQuery.data;

  // Load text review for the active run (needed for comparison view & review)
  const textReviewQuery = useTextReviewQuery(
    workspaceId,
    collectionId,
    sourceId,
    revisionId,
    selectedRunId,
    null,
    { enabled: Boolean(selectedRunId && activeRun?.status === "completed") },
  );

  const handleSelectRun = (runItem: ProcessingRunResponse) => {
    if (
      runItem.id !== selectedRunId &&
      hasUnsavedDraft &&
      !window.confirm(
        "Bạn có thay đổi hậu OCR chưa lưu ở lượt OCR hiện tại. Chuyển sang lượt khác sẽ giữ bản nháp cũ trong phiên này nhưng không áp dụng sang lượt mới. Tiếp tục?",
      )
    ) {
      return;
    }
    setSelectedRunId(runItem.id);
    setActivePage(1);
    setActiveSubTab("comparison");
    onDeepLinkChange?.({
      runId: runItem.id,
      page: 1,
      subTab: "comparison",
      checkId: undefined,
    });
  };

  const handlePageChange = (newPage: number) => {
    setActivePage(newPage);
    onDeepLinkChange?.({
      runId: selectedRunId ?? undefined,
      page: newPage,
      subTab: activeSubTab,
    });
  };

  const handleSubTabChange = (newTab: string) => {
    const validTab = newTab as OcrSubTab;
    setActiveSubTab(validTab);
    onDeepLinkChange?.({
      runId: selectedRunId ?? undefined,
      page: activePage,
      subTab: validTab,
    });
  };

  const statusInfo = activeRun ? formatRunStatus(activeRun.status) : null;
  const isDocxFile = isDocx(contentType, fileName);

  const draftScope = useMemo<OcrDraftScope | null>(
    () =>
      selectedRunId
        ? {
            workspaceId,
            collectionId,
            sourceId,
            revisionId,
            runId: selectedRunId,
          }
        : null,
    [collectionId, revisionId, selectedRunId, sourceId, workspaceId],
  );
  // Read-only view of the stored draft so the container can warn before the
  // scope changes and mark the review tab.
  const currentDraft = useOcrDraft(draftScope, null).draft;
  const draftCount = currentDraft?.changes.size ?? 0;
  const hasUnsavedDraft = draftCount > 0;
  const draftCountId = useId();

  // Leaving the page with an unsaved draft asks first. The draft itself is kept
  // in the session store, so returning to the same run restores it.
  const shouldBlockLeave = useCallback(() => {
    if (!hasUnsavedDraft) return false;
    return !window.confirm(
      "Bạn có thay đổi hậu OCR chưa lưu. Bản nháp vẫn được giữ trong phiên làm việc này nhưng chưa ghi vào server. Tiếp tục rời trang?",
    );
  }, [hasUnsavedDraft]);

  useBlocker({
    shouldBlockFn: shouldBlockLeave,
    enableBeforeUnload: () => hasUnsavedDraft,
    disabled: !hasUnsavedDraft,
  });

  return (
    <div className="space-y-4">
      {/* Header bar for OCR operations */}
      <Card className="rounded-xl shadow-2xs">
        <CardContent className="p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 text-xs">
          <div className="space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <Cpu className="size-4 text-primary" />
              <span className="font-semibold text-sm text-foreground">
                Xử lý OCR & Rà soát văn bản
              </span>
              <Badge variant="outline" className="font-mono text-xs">
                v{revisionNo}
              </Badge>
              {activeRun && statusInfo ? (
                <div className="flex items-center gap-1.5 ml-2">
                  <Badge
                    variant="default"
                    className="font-mono text-[11px] py-0"
                  >
                    Gen #{activeRun.generation}
                  </Badge>
                  <Badge
                    variant={statusInfo.variant}
                    className="text-[11px] py-0"
                  >
                    {statusInfo.label}
                  </Badge>
                  {activeRun.status === "running" ? (
                    <Loader2 className="size-3 animate-spin text-primary" />
                  ) : null}
                </div>
              ) : null}
            </div>
            <p className="text-muted-foreground text-[11px]">
              Tệp: <span className="font-mono font-medium">{fileName}</span> ·
              Bằng chứng OCR được ghim theo thế hệ bất biến.
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {canManage ? (
              <Button
                size="sm"
                className="h-8 text-xs gap-1.5"
                onClick={() => setRequestDialogOpen(true)}
              >
                <Play className="size-3.5" />
                <span>Yêu cầu OCR</span>
              </Button>
            ) : null}
          </div>
        </CardContent>
      </Card>

      {activeRun && ["failed", "uncertain"].includes(activeRun.status) && (
        <Alert variant="destructive" role="alert">
          <AlertCircle className="size-4" />
          <AlertTitle>OCR chưa hoàn tất</AlertTitle>
          <AlertDescription>
            {formatOcrError(activeRun.error_code, activeRun.error_detail)}
            {activeRun.error_code && (
              <span className="block font-mono text-xs">
                {activeRun.error_code}
              </span>
            )}
          </AlertDescription>
        </Alert>
      )}

      {/* Main Tabs within OCR Container */}
      {hasUnsavedDraft ? (
        // Kept outside the tab so it never joins the tab's accessible name.
        <span id={draftCountId} className="sr-only">
          {draftCount} thay đổi nháp chưa lưu
        </span>
      ) : null}
      <Tabs
        value={activeSubTab}
        onValueChange={handleSubTabChange}
        className="w-full space-y-4"
      >
        <div className="flex items-center justify-between border-b pb-2">
          <TabsList className="h-9">
            <TabsTrigger value="runs" className="text-xs gap-1.5">
              <ListOrdered className="size-3.5 text-primary" />
              <span>Lịch sử lượt OCR ({runs.length})</span>
            </TabsTrigger>

            <TabsTrigger
              value="comparison"
              disabled={!selectedRunId}
              className="text-xs gap-1.5"
            >
              <ImageIcon className="size-3.5 text-primary" />
              <span>Đối chiếu ảnh & Văn bản</span>
            </TabsTrigger>

            <TabsTrigger
              value="review"
              disabled={!selectedRunId || activeRun?.status !== "completed"}
              className="text-xs gap-1.5"
              aria-describedby={hasUnsavedDraft ? draftCountId : undefined}
            >
              <FileCheck2 className="size-3.5 text-primary" />
              <span>Rà soát &amp; Sửa bản dẫn xuất</span>
              {hasUnsavedDraft ? (
                // The count is supplementary: it must not change the tab's
                // accessible name, so it is exposed as a description instead.
                <Badge
                  variant="warning"
                  className="ml-1 text-[10px] py-0 px-1.5"
                  aria-hidden="true"
                >
                  {draftCount}
                </Badge>
              ) : null}
            </TabsTrigger>

            <TabsTrigger
              value="artifacts"
              disabled={!selectedRunId}
              className="text-xs gap-1.5"
            >
              <Layers className="size-3.5 text-primary" />
              <span>Artifacts & Kỹ thuật</span>
            </TabsTrigger>
          </TabsList>
        </div>

        {/* Tab 1: Runs List */}
        <TabsContent value="runs" className="mt-0">
          <OcrRunsList
            workspaceId={workspaceId}
            collectionId={collectionId}
            sourceId={sourceId}
            revisionId={revisionId}
            selectedRunId={selectedRunId}
            onSelectRun={handleSelectRun}
            canManage={canManage}
            page={runsListPage}
            onPageChange={setRunsListPage}
          />
        </TabsContent>

        {/* Tab 2: Side-by-side Page Comparison */}
        <TabsContent value="comparison" className="mt-0">
          {activeRun ? (
            <OcrComparisonView
              workspaceId={workspaceId}
              collectionId={collectionId}
              sourceId={sourceId}
              revisionId={revisionId}
              run={activeRun}
              pages={activeRun.pages}
              activePageNumber={activePage}
              onPageChange={handlePageChange}
              reviewDoc={textReviewQuery.data}
              isDocx={isDocxFile}
            />
          ) : (
            <Card className="p-8 text-center text-xs text-muted-foreground">
              Vui lòng chọn một lượt xử lý OCR từ danh sách để xem đối chiếu.
            </Card>
          )}
        </TabsContent>

        {/* Tab 3: Text Review & Post-OCR Corrections */}
        <TabsContent value="review" className="mt-0">
          {activeRun && activeRun.status === "completed" ? (
            <OcrTextReviewPanel
              workspaceId={workspaceId}
              collectionId={collectionId}
              sourceId={sourceId}
              revisionId={revisionId}
              run={activeRun}
              canManage={canManage}
              checkId={initialRunId === activeRun.id ? checkId : undefined}
              onCheckChange={(id) =>
                onDeepLinkChange?.({
                  runId: activeRun.id,
                  subTab: "review",
                  checkId: id,
                })
              }
            />
          ) : activeRun && activeRun.status !== "completed" ? (
            <Card className="p-6 text-center text-xs text-muted-foreground">
              <AlertCircle className="size-6 text-warning mx-auto mb-2" />
              <p className="font-semibold text-foreground">
                Lượt xử lý chưa hoàn tất thành công (Trạng thái:{" "}
                {statusInfo?.label}).
              </p>
              <p className="mt-1">
                Chức năng rà soát và sửa bản dẫn xuất chỉ khả dụng khi lượt OCR
                đã hoàn tất.
              </p>
            </Card>
          ) : (
            <Card className="p-8 text-center text-xs text-muted-foreground">
              Vui lòng chọn một lượt xử lý OCR hoàn tất để rà soát văn bản.
            </Card>
          )}
        </TabsContent>

        {/* Tab 4: Technical Artifacts & Snapshot */}
        <TabsContent value="artifacts" className="mt-0">
          {activeRun ? (
            <OcrArtifactsPanel
              workspaceId={workspaceId}
              collectionId={collectionId}
              sourceId={sourceId}
              revisionId={revisionId}
              run={activeRun}
            />
          ) : (
            <Card className="p-8 text-center text-xs text-muted-foreground">
              Vui lòng chọn một lượt xử lý OCR để xem tệp artifacts.
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* OCR Request Dialog */}
      <OcrRequestDialog
        workspaceId={workspaceId}
        collectionId={collectionId}
        sourceId={sourceId}
        revisionId={revisionId}
        revisionNo={revisionNo}
        fileName={fileName}
        isOpen={requestDialogOpen}
        onClose={() => setRequestDialogOpen(false)}
        onSuccess={(newRunId) => {
          setSelectedRunId(newRunId);
          setActiveSubTab("runs");
        }}
      />
    </div>
  );
}
