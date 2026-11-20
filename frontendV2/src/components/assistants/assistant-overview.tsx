import { Link } from "@tanstack/react-router";
import {
  Activity,
  ChevronRight,
  ExternalLink,
  Globe,
  ListChecks,
  MessageSquare,
  RefreshCw,
} from "lucide-react";
import { useAnswerReviewsQuery } from "@/api/answer-reviews";
import type { AssistantReadiness, AssistantResponse } from "@/api/assistants";
import { useAssistantConversationsQuery } from "@/api/conversations";
import { useCatalogQuery } from "@/api/modelops";
import { useAssistantPublicationQuery } from "@/api/publications";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { sanitizeDisplayText } from "@/lib/utils";
import {
  RETRIEVAL_OPTIONS,
  VERIFICATION_OPTIONS,
} from "./assistant-advanced-fields";
import {
  READINESS_MAP,
  readinessDetail,
  readinessHeroLabel,
  UNBOUND_DETAIL,
  UNBOUND_LABEL,
} from "./readiness";

const dateTimeFormatter = new Intl.DateTimeFormat("vi-VN", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return dateTimeFormatter.format(date);
}

const REVIEW_STATUS_MAP = {
  running: { label: "Đang chạy", variant: "info" },
  completed: { label: "Hoàn tất", variant: "success" },
  failed: { label: "Lỗi", variant: "destructive" },
  uncertain: { label: "Chưa xác định", variant: "warning" },
} as const;

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-muted/30 p-3 flex flex-col justify-between">
      <span className="text-[11px] font-medium text-muted-foreground">
        {label}
      </span>
      <span className="text-base font-semibold tracking-tight text-foreground mt-1 truncate">
        {value}
      </span>
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-t border-border/40 py-2 first:border-t-0 first:pt-0 last:pb-0">
      <span className="text-[11px] text-muted-foreground">{label}</span>
      <span className="truncate text-right text-xs font-medium text-foreground">
        {value}
      </span>
    </div>
  );
}

export function AssistantOverview({
  workspaceId,
  assistant,
  readiness,
  isRefreshingReadiness,
  onRefreshReadiness,
}: {
  workspaceId: string;
  assistant: AssistantResponse;
  readiness: AssistantReadiness | undefined;
  isRefreshingReadiness: boolean;
  onRefreshReadiness: () => void;
}) {
  const { data: catalog = [] } = useCatalogQuery(workspaceId);
  const conversationsQuery = useAssistantConversationsQuery(
    workspaceId,
    assistant.id,
  );
  const reviewsQuery = useAnswerReviewsQuery(workspaceId, assistant.id);
  const { data: publication } = useAssistantPublicationQuery(
    workspaceId,
    assistant.id,
  );

  const model = assistant.chat_provider_id
    ? catalog.find((item) => item.id === assistant.chat_provider_id)
    : null;
  const modelName = assistant.chat_provider_id
    ? (model?.model_name ?? "Mô hình không còn trong danh mục")
    : "Tự động theo hệ thống";
  const retrievalLabel =
    RETRIEVAL_OPTIONS.find(
      (option) => option.value === assistant.rag_policy.retrieval_mode,
    )?.label ?? assistant.rag_policy.retrieval_mode;
  const verificationLabel =
    VERIFICATION_OPTIONS.find(
      (option) => option.value === assistant.rag_policy.verification_mode,
    )?.label ?? "Tắt";

  const isUnbound = (assistant.collection_ids?.length ?? 0) === 0;
  const readinessBadge = readiness ? READINESS_MAP[readiness.status] : null;
  const readinessCollections = readiness?.collections ?? [];
  const collectionSummary = isUnbound
    ? "Chưa gắn kho tri thức"
    : readinessCollections.length > 1
      ? `${readinessCollections.length} kho · ${readinessCollections
          .map((item) => sanitizeDisplayText(item.collection_name))
          .join(", ")}`
      : sanitizeDisplayText(
          readinessCollections[0]?.collection_name ??
            readiness?.collection_name ??
            "Kho tri thức liên kết",
        );
  const conversations = (conversationsQuery.data ?? []).slice(0, 5);
  const latestReview = reviewsQuery.data?.[0] ?? null;
  const answeredCount =
    latestReview?.items.filter((item) => item.status === "answered").length ??
    0;

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card className="border-border/60 shadow-2xs lg:col-span-2">
        <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-3">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Activity className="size-4 text-primary" />
              <span>Trạng thái phục vụ</span>
              {readinessBadge ? (
                <Badge
                  variant={readinessBadge.variant}
                  className="h-5 px-1.5 text-[11px] font-normal"
                >
                  {isUnbound
                    ? UNBOUND_LABEL
                    : readinessHeroLabel(readiness?.status ?? "uncertain")}
                </Badge>
              ) : null}
            </CardTitle>
            <CardDescription>
              {isUnbound
                ? UNBOUND_DETAIL
                : readiness
                  ? readinessDetail(
                      readiness.status,
                      readiness.served_document_count,
                      readiness.published_document_count,
                    )
                  : "Chưa kiểm tra được trạng thái phục vụ."}
            </CardDescription>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 gap-1.5 text-xs"
            disabled={isRefreshingReadiness}
            onClick={onRefreshReadiness}
          >
            <RefreshCw
              className={`size-3.5 ${
                isRefreshingReadiness ? "animate-spin" : ""
              }`}
            />
            <span>Làm mới</span>
          </Button>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-2 sm:grid-cols-4">
            <Metric
              label="Tài liệu xuất bản"
              value={String(readiness?.published_document_count ?? 0)}
            />
            <Metric
              label="Đang phục vụ"
              value={String(readiness?.served_document_count ?? 0)}
            />
            <Metric
              label="Chỉ mục"
              value={
                readiness?.index_generation != null
                  ? `Thế hệ ${readiness.index_generation}`
                  : "—"
              }
            />
            <Metric
              label="Kiểm tra lúc"
              value={formatDateTime(readiness?.checked_at)}
            />
          </div>
          {readinessCollections.length > 1 ? (
            <div className="space-y-1">
              {readinessCollections.map((collection) => (
                <div
                  key={collection.collection_id}
                  className="flex items-center justify-between gap-2 rounded-md bg-muted/30 px-2.5 py-1.5"
                >
                  <span className="truncate text-[11px] text-foreground">
                    {sanitizeDisplayText(collection.collection_name)}
                  </span>
                  <span className="shrink-0 text-[11px] text-muted-foreground">
                    {collection.served_document_count}/
                    {collection.published_document_count} tài liệu
                  </span>
                  <Badge
                    variant={READINESS_MAP[collection.status].variant}
                    className="h-5 shrink-0 px-1.5 text-[10px] font-normal"
                  >
                    {READINESS_MAP[collection.status].label}
                  </Badge>
                </div>
              ))}
            </div>
          ) : null}
          {readiness?.sync_error_code ? (
            <p className="rounded-md border border-destructive/30 bg-destructive/10 px-2.5 py-2 text-[11px] text-destructive">
              Đồng bộ chỉ mục báo lỗi: {readiness.sync_error_code}
            </p>
          ) : null}
        </CardContent>
      </Card>

      <Card className="border-border/60 shadow-2xs">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Cấu hình đang áp dụng</CardTitle>
          <CardDescription>Tóm tắt cấu hình đang phục vụ.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-1">
          <SummaryRow label="Mô hình" value={modelName} />
          <SummaryRow label="Kho tri thức" value={collectionSummary} />
          <SummaryRow label="Truy xuất" value={retrievalLabel} />
          <SummaryRow
            label="Trích dẫn"
            value={`${assistant.top_k} đoạn · ${assistant.history_turns} lượt ghi nhớ`}
          />
          <SummaryRow label="Kiểm chứng" value={verificationLabel} />
          <SummaryRow
            label="Kênh công khai"
            value={
              publication?.enabled
                ? `Đang bật (/${publication.slug})`
                : "Chưa công khai"
            }
          />
          <SummaryRow
            label="Phiên bản"
            value={`${assistant.revision} · ${formatDateTime(assistant.updated_at)}`}
          />
          <div className="pt-2">
            <Button
              asChild
              variant="link"
              size="sm"
              className="h-6 gap-0.5 px-0 text-xs"
            >
              <Link
                to="/assistants/$assistantId"
                params={{ assistantId: assistant.id }}
                search={{ tab: "config" }}
              >
                <span>Chỉnh cấu hình</span>
                <ChevronRight className="size-3.5" />
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/60 shadow-2xs lg:col-span-2">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-sm">
              <MessageSquare className="size-4 text-primary" />
              <span>Hội thoại gần đây</span>
            </CardTitle>
            <CardDescription>
              {conversationsQuery.data?.length
                ? `${conversationsQuery.data.length} hội thoại đã lưu · Hiển thị 5 gần nhất`
                : "Năm hội thoại cập nhật gần nhất của trợ lý."}
            </CardDescription>
          </div>
          <Button
            asChild
            variant="ghost"
            size="sm"
            className="h-7 gap-0.5 px-2 text-xs"
          >
            <Link
              to="/assistants/$assistantId"
              params={{ assistantId: assistant.id }}
              search={{ tab: "logs" }}
            >
              <span>
                {conversationsQuery.data?.length
                  ? `Toàn bộ (${conversationsQuery.data.length})`
                  : "Nhật ký"}
              </span>
              <ChevronRight className="size-3.5" />
            </Link>
          </Button>
        </CardHeader>
        <CardContent>
          {conversationsQuery.isLoading ? (
            <div className="space-y-2">
              {["one", "two", "three"].map((slot) => (
                <Skeleton
                  key={`overview-conversation-${slot}`}
                  className="h-10 rounded-md"
                />
              ))}
            </div>
          ) : conversationsQuery.isError ? (
            <p className="text-xs text-destructive">
              Không tải được hội thoại gần đây.
            </p>
          ) : conversations.length === 0 ? (
            <div className="flex flex-col items-start gap-2 rounded-md bg-muted/30 px-3 py-3">
              <p className="text-xs text-muted-foreground">
                Chưa có hội thoại nào với trợ lý này.
              </p>
              <Button
                asChild
                variant="outline"
                size="sm"
                className="h-7 text-xs"
              >
                <Link
                  to="/assistants/$assistantId"
                  params={{ assistantId: assistant.id }}
                  search={{ tab: "ask" }}
                >
                  Hỏi thử ngay
                </Link>
              </Button>
            </div>
          ) : (
            <div className="space-y-1">
              {conversations.map((conversation) => (
                <Link
                  key={conversation.id}
                  to="/assistants/$assistantId"
                  params={{ assistantId: assistant.id }}
                  search={{ tab: "logs" }}
                  className="flex items-center justify-between gap-3 rounded-md px-2.5 py-2 transition-colors hover:bg-muted/50 border border-transparent hover:border-border/50"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <MessageSquare className="size-3.5 text-muted-foreground shrink-0" />
                    <span className="truncate text-xs font-medium text-foreground">
                      {conversation.title || "Hội thoại chưa đặt tên"}
                    </span>
                  </div>
                  <span className="shrink-0 text-[11px] text-muted-foreground">
                    {conversation.last_turn_no} lượt ·{" "}
                    {formatDateTime(conversation.updated_at)}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="space-y-4">
        {publication?.enabled ? (
          <Card className="border-border/60 shadow-2xs">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <div className="space-y-0.5">
                <CardTitle className="flex items-center gap-1.5 text-sm">
                  <Globe className="size-4 text-primary" />
                  <span>Cổng trực tuyến</span>
                </CardTitle>
                <CardDescription>
                  Đang mở tiếp nhận câu hỏi trực tuyến.
                </CardDescription>
              </div>
              <Badge
                variant="outline"
                className="h-5 gap-1 border-primary/30 bg-primary/10 px-1.5 text-[10px] font-medium text-primary"
              >
                <span className="size-1.5 rounded-full bg-emerald-500" />
                <span>Hoạt động</span>
              </Badge>
            </CardHeader>
            <CardContent className="space-y-2 pt-1 text-xs">
              <div className="flex items-center justify-between gap-2 rounded-lg bg-muted/40 px-2.5 py-1.5 font-mono text-xs text-foreground">
                <span className="truncate">/{publication.slug}</span>
                <Button
                  asChild
                  variant="ghost"
                  size="sm"
                  className="h-6 gap-1 px-1.5 text-[11px] text-primary hover:text-primary"
                >
                  <a
                    href={`/chatbot/${publication.slug}`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <span>Mở cổng</span>
                    <ExternalLink className="size-3" />
                  </a>
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : null}

        <Card className="border-border/60 shadow-2xs">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
            <div className="space-y-1">
              <CardTitle className="flex items-center gap-2 text-sm">
                <ListChecks className="size-4 text-primary" />
                <span>Kiểm thử gần đây</span>
              </CardTitle>
              <CardDescription>Lần chạy thử mới nhất.</CardDescription>
            </div>
            <Button
              asChild
              variant="ghost"
              size="sm"
              className="h-7 gap-0.5 px-2 text-xs"
            >
              <Link
                to="/assistants/$assistantId"
                params={{ assistantId: assistant.id }}
                search={{ tab: "reviews" }}
              >
                <span>Tất cả</span>
                <ChevronRight className="size-3.5" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            {reviewsQuery.isLoading ? (
              <Skeleton className="h-14 rounded-md" />
            ) : reviewsQuery.isError ? (
              <p className="text-xs text-destructive">
                Không tải được lịch sử kiểm thử.
              </p>
            ) : !latestReview ? (
              <div className="flex flex-col items-start gap-2 rounded-md bg-muted/30 p-3">
                <p className="text-xs font-medium text-foreground">
                  Chưa có đợt kiểm thử nào
                </p>
                <p className="text-[11px] leading-relaxed text-muted-foreground">
                  Thực hiện hỏi thử để kiểm tra câu trả lời, sau đó chấm nhãn độ
                  chính xác để theo dõi chất lượng.
                </p>
                <Button
                  asChild
                  variant="outline"
                  size="sm"
                  className="mt-1 h-7 text-xs font-medium"
                >
                  <Link
                    to="/assistants/$assistantId"
                    params={{ assistantId: assistant.id }}
                    search={{ tab: "ask" }}
                  >
                    Mở Hỏi thử để đánh giá
                  </Link>
                </Button>
              </div>
            ) : (
              <div className="space-y-1.5">
                <div className="flex items-center gap-2">
                  <Badge
                    variant={REVIEW_STATUS_MAP[latestReview.status].variant}
                    className="h-5 px-1.5 text-[11px] font-normal"
                  >
                    {REVIEW_STATUS_MAP[latestReview.status].label}
                  </Badge>
                  <span className="text-[11px] text-muted-foreground">
                    {formatDateTime(latestReview.created_at)}
                  </span>
                </div>
                <p className="text-xs text-foreground">
                  {latestReview.question_count} câu hỏi · {answeredCount} câu
                  trả lời được
                </p>
                <p className="text-[11px] text-muted-foreground">
                  Chạy trên phiên bản {latestReview.assistant_revision} của trợ
                  lý.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
