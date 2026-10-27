import {
  AlertCircle,
  CheckCircle2,
  FileCheck2,
  Filter,
  Info,
  Loader2,
  Plus,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/app/api/v1";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useCatalogQuery } from "@/features/modelops/queries";
import { formatDateTimeValue } from "@/lib/date-utils";
import {
  useAutoReviewQuery,
  useCompilationReviewQuery,
  useCompilationReviewReportQuery,
  useCompilationReviewsQuery,
  useCreateReviewMutation,
} from "./compilation-queries";
import {
  formatAutoReviewStatus,
  formatCompilationError,
  formatDraftAssessmentStatus,
  formatReviewVerdict,
  formatSourceAssessmentStatus,
  generateIdempotencyKey,
} from "./compilation-schemas";
import type {
  CompilationReviewResponse,
  ReviewFinding,
  ReviewReportResponse,
  ReviewRequestInput,
  UnitExcerpt,
} from "./compilation-types";
import { ListPagination } from "./list-pagination";
import { ReviewDownloads } from "./review-downloads";

export function CompilationReviewTab({
  workspaceId,
  collectionId,
  runId,
  canReview,
  page = 1,
  pageSize = 20,
  reviewId,
  onSearchChange,
}: {
  workspaceId: string;
  collectionId: string;
  runId: string;
  canReview: boolean;
  page?: number;
  pageSize?: number;
  reviewId?: string;
  onSearchChange?: (patch: {
    reviewPage?: number;
    reviewPageSize?: number;
    reviewId?: string;
  }) => void;
}) {
  const [selectedReviewId, setSelectedReviewId] = useState<string | null>(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);

  // Auto-review status query
  const autoReviewQuery = useAutoReviewQuery(workspaceId, collectionId, runId);

  // Reviews listing query
  const reviewsQuery = useCompilationReviewsQuery(
    workspaceId,
    collectionId,
    runId,
    pageSize,
    (page - 1) * pageSize,
    { lookahead: true },
  );

  const reviews = (reviewsQuery.data ?? []).slice(0, pageSize);

  // Determine current active review id: user selection or latest completed review or auto review
  const activeReviewId =
    (onSearchChange ? reviewId : selectedReviewId) ??
    (page === 1 ? autoReviewQuery.data?.review_id : undefined) ??
    reviews[0]?.id ??
    null;

  const activeReviewQuery = useCompilationReviewQuery(
    workspaceId,
    collectionId,
    runId,
    activeReviewId,
  );

  const reportQuery = useCompilationReviewReportQuery(
    workspaceId,
    collectionId,
    runId,
    activeReviewId,
    {
      enabled: Boolean(
        activeReviewId && activeReviewQuery.data?.status === "completed",
      ),
    },
  );

  const autoReviewData = autoReviewQuery.data;
  const isAutoReviewPending =
    autoReviewData &&
    !autoReviewData.notScheduled &&
    (autoReviewData.status === "queued" || autoReviewData.status === "running");

  return (
    <div className="space-y-6">
      {/* Auto-Review & Reviews Header Bar */}
      <Card className="rounded-xl shadow-2xs">
        <CardContent className="p-4 sm:p-5 space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2 flex-wrap">
                <FileCheck2 className="size-4 text-primary" />
                <span className="font-semibold text-sm text-foreground">
                  Rà soát & Đánh giá độc lập (Review)
                </span>

                {/* Auto Review Indicator */}
                {autoReviewData?.notScheduled ? (
                  <Badge
                    variant="outline"
                    className="text-[11px] text-muted-foreground"
                  >
                    Không có Auto-Review
                  </Badge>
                ) : autoReviewData ? (
                  <Badge
                    variant={
                      formatAutoReviewStatus(autoReviewData.status).variant
                    }
                    className="text-[11px]"
                  >
                    Auto-Review:{" "}
                    {formatAutoReviewStatus(autoReviewData.status).label}
                  </Badge>
                ) : null}

                {isAutoReviewPending && (
                  <Loader2 className="size-3.5 animate-spin text-primary" />
                )}
              </div>

              <p className="text-xs text-muted-foreground">
                Đánh giá hai chiều giữa bằng chứng nguồn và bản nháp biên soạn.
                Kiểm tra bỏ sót và sai diễn giải.
              </p>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              {canReview && (
                <Button
                  size="sm"
                  className="h-8 text-xs gap-1.5"
                  onClick={() => setCreateDialogOpen(true)}
                >
                  <Plus className="size-3.5" />
                  <span>Yêu cầu Review thủ công</span>
                </Button>
              )}
            </div>
          </div>

          {/* Review Switcher if multiple reviews exist */}
          {reviews.length > 1 && (
            <div className="flex items-center gap-2 pt-2 border-t text-xs">
              <span className="text-muted-foreground whitespace-nowrap">
                Chọn đợt review:
              </span>
              <Select
                value={activeReviewId ?? ""}
                onValueChange={(val) => {
                  setSelectedReviewId(val);
                  onSearchChange?.({ reviewId: val });
                }}
              >
                <SelectTrigger className="h-7 text-xs w-[280px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {reviews.map((r) => (
                    <SelectItem
                      key={r.id}
                      value={r.id}
                      className="text-xs font-mono"
                    >
                      {r.id.slice(0, 12)}... · {r.verdict || r.status} (
                      {formatDateTimeValue(r.created_at)})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
        </CardContent>
      </Card>

      <ListPagination
        page={page}
        pageSize={pageSize}
        hasNext={
          !reviewsQuery.isError && (reviewsQuery.data?.length ?? 0) > pageSize
        }
        disabled={reviewsQuery.isFetching}
        label="review Compiler"
        onPageChange={
          onSearchChange
            ? (page) => {
                setSelectedReviewId(null);
                onSearchChange({ reviewPage: page, reviewId: undefined });
              }
            : undefined
        }
        onPageSizeChange={
          onSearchChange
            ? (pageSize) => {
                setSelectedReviewId(null);
                onSearchChange({
                  reviewPage: 1,
                  reviewPageSize: pageSize,
                  reviewId: undefined,
                });
              }
            : undefined
        }
      />
      {/* Main Review Report Content */}
      {activeReviewId && activeReviewQuery.data?.id === activeReviewId ? (
        <ReviewDownloads
          workspaceId={workspaceId}
          collectionId={collectionId}
          runId={runId}
          reviewId={activeReviewId}
          status={activeReviewQuery.data.status}
        />
      ) : null}
      {reviewsQuery.isLoading || autoReviewQuery.isLoading ? (
        <Skeleton className="h-24 w-full" />
      ) : reviewsQuery.isError || autoReviewQuery.isError ? (
        <Alert variant="destructive">
          <AlertDescription>
            Không thể tải trạng thái rà soát. Vui lòng kiểm tra lại.
          </AlertDescription>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              void reviewsQuery.refetch();
              void autoReviewQuery.refetch();
            }}
          >
            Tải lại
          </Button>
        </Alert>
      ) : !activeReviewId ? (
        <Card className="rounded-xl shadow-2xs">
          <CardContent className="py-12 text-center space-y-2">
            <div className="size-10 rounded-full bg-muted flex items-center justify-center mx-auto text-muted-foreground">
              <FileCheck2 className="size-5" />
            </div>
            <h3 className="text-sm font-semibold text-foreground">
              Chưa có báo cáo review nào
            </h3>
            <p className="text-xs text-muted-foreground max-w-sm mx-auto">
              {isAutoReviewPending
                ? "Hệ thống đang tiến hành rà soát tự động, vui lòng chờ trong giây lát..."
                : "Bạn có thể chủ động yêu cầu reviewer rà soát và đánh giá tính trung thực của bản biên soạn."}
            </p>
            {canReview && !isAutoReviewPending && (
              <Button
                size="sm"
                className="h-8 text-xs gap-1.5 mt-2"
                onClick={() => setCreateDialogOpen(true)}
              >
                <Plus className="size-3.5" />
                <span>Bắt đầu rà soát</span>
              </Button>
            )}
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                void autoReviewQuery.refetch();
                void reviewsQuery.refetch();
              }}
            >
              Kiểm tra lại
            </Button>
          </CardContent>
        </Card>
      ) : activeReviewQuery.isLoading || reportQuery.isLoading ? (
        <Card className="rounded-xl shadow-2xs p-5 space-y-4">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-48 w-full" />
        </Card>
      ) : activeReviewQuery.data?.status === "running" ||
        activeReviewQuery.data?.status === "queued" ? (
        <Card className="rounded-xl shadow-2xs p-6 text-center space-y-3">
          <Loader2 className="size-6 animate-spin text-primary mx-auto" />
          <div className="space-y-1">
            <h3 className="text-sm font-semibold text-foreground">
              Mô hình đang rà soát độc lập...
            </h3>
            <p className="text-xs text-muted-foreground">
              Quá trình kiểm tra hai chiều bao quát toàn bộ source units và
              draft units.
            </p>
          </div>
        </Card>
      ) : reportQuery.isError ||
        !reportQuery.data ||
        !activeReviewQuery.data ? (
        <Card className="rounded-xl border-destructive/20 bg-destructive/5 p-4 text-xs">
          <div className="flex items-center gap-2 text-destructive font-semibold">
            <AlertCircle className="size-4 shrink-0" />
            <span>Không thể tải báo cáo review</span>
          </div>
          <p className="text-muted-foreground mt-1">
            {reportQuery.error instanceof Error
              ? reportQuery.error.message
              : "Reviewer chưa hoàn tất hoặc gặp sự cố kiểm tra."}
          </p>
        </Card>
      ) : (
        <ReportViewer
          report={reportQuery.data}
          review={activeReviewQuery.data}
        />
      )}

      {/* Manual Review Creation Dialog */}
      <CreateReviewDialog
        workspaceId={workspaceId}
        collectionId={collectionId}
        runId={runId}
        isOpen={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        onSuccess={(reviewId) => setSelectedReviewId(reviewId)}
      />
    </div>
  );
}

function ReportViewer({
  report,
  review,
}: {
  report: ReviewReportResponse;
  review: CompilationReviewResponse;
}) {
  const [activeTab, setActiveTab] = useState<
    "findings" | "source_assessments" | "draft_assessments"
  >("findings");
  const [findingsFilter, setFindingsFilter] = useState<string>("all");

  const verdictInfo = formatReviewVerdict(report.verdict);

  const filteredFindings = report.findings.filter((f) => {
    if (findingsFilter === "all") return true;
    return f.status === findingsFilter;
  });

  return (
    <div className="space-y-4">
      {/* Verdict & KPI Banner */}
      <Card
        className={`rounded-xl shadow-2xs border ${
          report.verdict === "needs_attention"
            ? "border-destructive/30 bg-destructive/5"
            : "border-success/30 bg-success/5"
        }`}
      >
        <CardContent className="p-4 sm:p-5 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Badge
                  variant={verdictInfo.variant}
                  className="text-xs px-2.5 py-0.5 font-semibold"
                >
                  {verdictInfo.label}
                </Badge>
                <span className="text-xs text-muted-foreground font-mono">
                  Review ID: {report.review_id.slice(0, 12)}...
                </span>
              </div>
              <p className="text-xs text-foreground/80 pt-1 leading-relaxed">
                {verdictInfo.description}
              </p>
            </div>
          </div>

          {/* Metrics summary */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t text-xs">
            <div className="space-y-0.5">
              <span className="text-muted-foreground text-[11px]">
                Nguồn đã kiểm:
              </span>
              <p className="font-mono font-semibold text-foreground text-sm">
                {report.summary.source_units_checked} units
              </p>
            </div>
            <div className="space-y-0.5">
              <span className="text-muted-foreground text-[11px]">
                Bản nháp đã kiểm:
              </span>
              <p className="font-mono font-semibold text-foreground text-sm">
                {report.summary.draft_units_checked} units
              </p>
            </div>
            <div className="space-y-0.5">
              <span className="text-muted-foreground text-[11px]">
                Vấn đề phát hiện:
              </span>
              <p
                className={`font-mono font-semibold text-sm ${
                  report.summary.finding_count > 0
                    ? "text-destructive"
                    : "text-success"
                }`}
              >
                {report.summary.finding_count} vấn đề
              </p>
            </div>
            <div className="space-y-0.5">
              <span className="text-muted-foreground text-[11px]">
                Reviewer model:
              </span>
              <p className="font-mono text-muted-foreground text-xs truncate">
                {review.provider_id || "Mặc định"}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tabs navigation: Findings vs 2-way Explorer */}
      <Tabs
        value={activeTab}
        onValueChange={(val) =>
          setActiveTab(
            val as "findings" | "source_assessments" | "draft_assessments",
          )
        }
      >
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b pb-2">
          <TabsList className="h-8 p-0.5 bg-muted/40 text-xs">
            <TabsTrigger value="findings" className="text-xs h-7 px-3">
              Các vấn đề phát hiện ({report.findings.length})
            </TabsTrigger>
            <TabsTrigger
              value="source_assessments"
              className="text-xs h-7 px-3"
            >
              Nguồn → Bản biên soạn ({report.source_assessments.length})
            </TabsTrigger>
            <TabsTrigger value="draft_assessments" className="text-xs h-7 px-3">
              Bản biên soạn → Nguồn ({report.draft_assessments.length})
            </TabsTrigger>
          </TabsList>

          {activeTab === "findings" && (
            <div className="flex items-center gap-1.5 text-xs">
              <Filter className="size-3.5 text-muted-foreground" />
              <Select
                value={findingsFilter}
                onValueChange={(val) => setFindingsFilter(val)}
              >
                <SelectTrigger className="h-7 text-xs w-[140px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all" className="text-xs">
                    Tất cả vấn đề
                  </SelectItem>
                  <SelectItem value="omitted" className="text-xs">
                    Bỏ sót ý
                  </SelectItem>
                  <SelectItem value="contradicted" className="text-xs">
                    Diễn giải sai
                  </SelectItem>
                  <SelectItem value="unsupported" className="text-xs">
                    Thiếu căn cứ
                  </SelectItem>
                  <SelectItem value="uncertain" className="text-xs">
                    Chưa chắc chắn
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}
        </div>

        {/* Tab 1: Findings List */}
        <TabsContent value="findings" className="space-y-3 pt-3">
          {filteredFindings.length === 0 ? (
            <Card className="rounded-xl p-8 text-center text-xs text-muted-foreground">
              <CheckCircle2 className="size-6 text-success mx-auto mb-2" />
              <p className="font-semibold text-foreground">
                Không có vấn đề nào phù hợp bộ lọc
              </p>
              <p className="text-[11px] text-muted-foreground/80 mt-1">
                Tất cả các nội dung đã kiểm tra đều đạt trạng thái phù hợp.
              </p>
            </Card>
          ) : (
            filteredFindings.map((finding, idx) => (
              <FindingCard
                // biome-ignore lint/suspicious/noArrayIndexKey: findings list ordered sequentially
                key={idx}
                finding={finding}
                index={idx + 1}
              />
            ))
          )}
        </TabsContent>

        {/* Tab 2: Source to Draft */}
        <TabsContent value="source_assessments" className="space-y-3 pt-3">
          {report.source_assessments.map((item) => {
            const statusInfo = formatSourceAssessmentStatus(item.status);
            return (
              <Card
                key={item.source_id}
                className="rounded-lg shadow-2xs text-xs"
              >
                <CardContent className="p-3.5 space-y-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <Badge
                      variant="outline"
                      className={`text-[10px] font-medium ${statusInfo.badgeClass}`}
                    >
                      {statusInfo.label}
                    </Badge>
                    <span className="font-mono text-[10px] text-muted-foreground">
                      ID: {item.source_id}
                    </span>
                  </div>

                  <div className="p-2 rounded bg-muted/20 border text-foreground text-xs leading-relaxed">
                    <span className="text-[11px] text-muted-foreground font-semibold block mb-0.5">
                      Nội dung nguồn:
                    </span>
                    {item.source?.text || "(Không có trích đoạn)"}
                  </div>

                  <div className="space-y-1">
                    <span className="text-muted-foreground font-semibold text-[11px]">
                      Giải thích:
                    </span>
                    <p className="text-foreground text-xs">
                      {item.explanation}
                    </p>
                  </div>

                  {item.suggested_action && (
                    <div className="text-[11px] text-primary bg-primary/5 p-2 rounded border border-primary/20">
                      <span className="font-semibold">Gợi ý xử lý:</span>{" "}
                      {item.suggested_action}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </TabsContent>

        {/* Tab 3: Draft to Source */}
        <TabsContent value="draft_assessments" className="space-y-3 pt-3">
          {report.draft_assessments.map((item) => {
            const statusInfo = formatDraftAssessmentStatus(item.status);
            return (
              <Card
                key={item.draft_id}
                className="rounded-lg shadow-2xs text-xs"
              >
                <CardContent className="p-3.5 space-y-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <Badge
                      variant="outline"
                      className={`text-[10px] font-medium ${statusInfo.badgeClass}`}
                    >
                      {statusInfo.label}
                    </Badge>
                    <span className="font-mono text-[10px] text-muted-foreground">
                      ID: {item.draft_id}
                    </span>
                  </div>

                  <div className="p-2 rounded bg-muted/20 border text-foreground text-xs leading-relaxed">
                    <span className="text-[11px] text-muted-foreground font-semibold block mb-0.5">
                      Đoạn biên soạn:
                    </span>
                    {item.draft?.text || "(Không có trích đoạn)"}
                  </div>

                  <div className="space-y-1">
                    <span className="text-muted-foreground font-semibold text-[11px]">
                      Giải thích:
                    </span>
                    <p className="text-foreground text-xs">
                      {item.explanation}
                    </p>
                  </div>

                  {item.suggested_action && (
                    <div className="text-[11px] text-primary bg-primary/5 p-2 rounded border border-primary/20">
                      <span className="font-semibold">Gợi ý xử lý:</span>{" "}
                      {item.suggested_action}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </TabsContent>
      </Tabs>

      {/* Limits & Disclaimer */}
      <Alert className="rounded-lg border-muted bg-muted/20 text-xs py-2.5">
        <Info className="size-3.5 text-muted-foreground shrink-0" />
        <AlertDescription className="text-muted-foreground text-[11px] space-y-1 leading-relaxed">
          <span className="font-semibold block text-foreground">
            Giới hạn của báo cáo rà soát:
          </span>
          <ul className="list-disc pl-4 space-y-0.5">
            {report.limits.map((l, i) => (
              <li
                // biome-ignore lint/suspicious/noArrayIndexKey: disclaimer bullet list
                key={i}
              >
                {l}
              </li>
            ))}
          </ul>
        </AlertDescription>
      </Alert>
    </div>
  );
}

export function FindingCard({
  finding,
  index,
}: {
  finding: ReviewFinding;
  index: number;
}) {
  const isSourceToDraft = finding.direction === "source_to_draft";
  const statusLabel =
    finding.status === "omitted"
      ? "Có thể bỏ sót ý"
      : finding.status === "contradicted"
        ? "Có thể diễn giải sai"
        : finding.status === "unsupported"
          ? "Chưa thấy căn cứ"
          : "Cần đối chiếu thêm";

  return (
    <Card className="rounded-xl shadow-2xs border-l-4 border-l-destructive text-xs">
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="flex items-center gap-2">
            <span className="font-mono font-semibold text-destructive">
              #{index}
            </span>
            <Badge
              variant="destructive"
              className="text-[10px] py-0 font-normal"
            >
              {statusLabel}
            </Badge>
            <span className="text-[11px] text-muted-foreground">
              {isSourceToDraft ? "Nguồn → Bản nháp" : "Bản nháp → Nguồn"}
            </span>
          </div>
        </div>

        <p className="text-foreground text-xs font-medium leading-relaxed">
          {finding.explanation}
        </p>

        {/* Excerpts comparison */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t">
          <div className="p-2.5 rounded-lg bg-muted/20 border space-y-1">
            <span className="text-[11px] font-semibold text-muted-foreground block">
              Trích đoạn nguồn:
            </span>
            {finding.sources.length === 0 ? (
              <span className="text-[11px] text-muted-foreground italic">
                (Không có trích đoạn nguồn liên kết)
              </span>
            ) : (
              finding.sources.map((s: UnitExcerpt, i: number) => (
                <div
                  key={s.id || `src-${i}-${s.page || 0}`}
                  className="text-xs text-foreground font-sans"
                >
                  {s.page ? (
                    <span className="font-mono text-[10px] text-primary block">
                      Trang {s.page}
                    </span>
                  ) : null}
                  {s.text}
                </div>
              ))
            )}
          </div>

          <div className="p-2.5 rounded-lg bg-muted/20 border space-y-1">
            <span className="text-[11px] font-semibold text-muted-foreground block">
              Trích đoạn bản biên soạn:
            </span>
            {finding.draft_excerpts.length === 0 ? (
              <span className="text-[11px] text-muted-foreground italic">
                (Không có trích đoạn bản nháp tương ứng)
              </span>
            ) : (
              finding.draft_excerpts.map((d: UnitExcerpt, i: number) => (
                <div
                  key={d.id || `draft-${i}`}
                  className="text-xs text-foreground font-sans"
                >
                  {d.text}
                </div>
              ))
            )}
          </div>
        </div>

        {finding.suggested_action && (
          <div className="pt-2 border-t text-[11px] text-primary bg-primary/5 p-2 rounded border border-primary/20">
            <span className="font-semibold">Gợi ý xử lý:</span>{" "}
            {finding.suggested_action}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function CreateReviewDialog({
  workspaceId,
  collectionId,
  runId,
  isOpen,
  onClose,
  onSuccess,
}: {
  workspaceId: string;
  collectionId: string;
  runId: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (reviewId: string) => void;
}) {
  const [providerId, setProviderId] = useState<string>("default");
  const [maxTokens, setMaxTokens] = useState<string>("8192");
  const [structuredOutput, setStructuredOutput] = useState<boolean>(false);
  const [idempotencyKey, setIdempotencyKey] = useState<string>(() =>
    generateIdempotencyKey(),
  );

  const catalogQuery = useCatalogQuery(workspaceId, { enabled: isOpen });
  const createMutation = useCreateReviewMutation(
    workspaceId,
    collectionId,
    runId,
  );

  const chatProviders = (catalogQuery.data ?? []).filter((p) =>
    p.capabilities.includes("chat"),
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const input: ReviewRequestInput = {
      provider_id: providerId === "default" ? null : providerId,
      max_output_tokens: maxTokens ? Number(maxTokens) : 8192,
      structured_output: structuredOutput,
    };

    try {
      const review = await createMutation.mutateAsync({
        input,
        idempotencyKey,
      });
      toast.success("Đã khởi động lượt review độc lập.");
      onClose();
      onSuccess?.(review.id);
    } catch (err: unknown) {
      if (err instanceof ApiProblemError) {
        toast.error(formatCompilationError(err.code, err.message));
      } else {
        toast.error("Không thể khởi động lượt review.");
      }
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-md p-0 flex flex-col gap-0">
        <DialogHeader className="p-4 border-b bg-muted/20">
          <div className="flex items-center gap-2">
            <FileCheck2 className="size-4 text-primary" />
            <DialogTitle className="text-base font-semibold">
              Yêu cầu rà soát độc lập (Review)
            </DialogTitle>
          </div>
          <DialogDescription className="text-xs text-muted-foreground">
            Mô hình AI độc lập sẽ đối chiếu hai chiều giữa bằng chứng nguồn và
            bản nháp.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="p-4 space-y-4 text-xs">
          <div className="space-y-1.5">
            <Label className="text-xs font-semibold">
              Reviewer Model (Capability Chat)
            </Label>
            <Select
              value={providerId}
              onValueChange={(val) => {
                setProviderId(val);
                setIdempotencyKey(generateIdempotencyKey());
              }}
            >
              <SelectTrigger className="h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="default" className="text-xs">
                  Mặc định chat của workspace (Khuyên dùng)
                </SelectItem>
                {chatProviders.map((p) => (
                  <SelectItem key={p.id} value={p.id} className="text-xs">
                    {p.name} ({p.model_name})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-[11px] text-muted-foreground">
              Review thủ công không chỉ định provider sẽ dùng mặc định chat hiện
              hành.
            </p>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs font-semibold">
              Giới hạn Output Tokens
            </Label>
            <Input
              type="number"
              min={1}
              className="h-8 text-xs font-mono"
              value={maxTokens}
              onChange={(e) => {
                setMaxTokens(e.target.value);
                setIdempotencyKey(generateIdempotencyKey());
              }}
            />
            <p className="text-[11px] text-muted-foreground">
              Mặc định 8192 tokens.
            </p>
          </div>

          <div className="flex items-center space-x-2 pt-1">
            <Checkbox
              id="manual-review-structured"
              checked={structuredOutput}
              onCheckedChange={(checked) => {
                setStructuredOutput(Boolean(checked));
                setIdempotencyKey(generateIdempotencyKey());
              }}
            />
            <Label
              htmlFor="manual-review-structured"
              className="text-xs font-normal text-muted-foreground cursor-pointer"
            >
              Bật Keyed Structured Output (Advanced)
            </Label>
          </div>

          <Alert className="rounded-lg border-info/30 bg-info/5 text-xs py-2">
            <Info className="size-3 text-info shrink-0" />
            <AlertDescription className="text-muted-foreground text-[11px]">
              Thao tác này sẽ phát sinh lượt gọi AI và tiêu tốn token quota của
              workspace.
            </AlertDescription>
          </Alert>

          <DialogFooter className="pt-2 border-t flex items-center justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-8 text-xs"
              onClick={onClose}
              disabled={createMutation.isPending}
            >
              Hủy
            </Button>
            <Button
              type="submit"
              size="sm"
              className="h-8 text-xs gap-1.5"
              disabled={createMutation.isPending}
            >
              {createMutation.isPending ? (
                <>
                  <Loader2 className="size-3 animate-spin" />
                  <span>Đang gửi...</span>
                </>
              ) : (
                <>
                  <FileCheck2 className="size-3.5" />
                  <span>Bắt đầu Review</span>
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
