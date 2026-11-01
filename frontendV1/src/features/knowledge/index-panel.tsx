import {
  AlertCircle,
  CheckCircle2,
  Database,
  Loader2,
  Play,
  RefreshCw,
  Search,
} from "lucide-react";
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";
import { toast } from "sonner";
import { ApiProblemError, getTokenState, subscribeToken } from "@/app/api/v1";
import type { CallerWorkspaceRole } from "@/app/auth/v1/permissions";
import { Field, FieldDescription, FieldLabel } from "@/components/admin/field";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useIndexRunsQuery,
  useRequestIndexMutation,
  useSearchMutation,
} from "@/features/knowledge/index-queries";
import {
  DEFAULT_SEARCH_INPUT,
  type IndexRun,
  type SearchResponse,
} from "@/features/knowledge/index-types";
import { LifecycleActions } from "@/features/lifecycle/lifecycle-actions";
import { useCatalogQuery } from "@/features/modelops/queries";
import {
  draftToFilter,
  EMPTY_METADATA_FILTER_DRAFT,
  type MetadataFilterDraft,
  MetadataFilterFields,
  validateMetadataFilterDraft,
} from "@/features/rag/metadata-filter-fields";
import { RETRIEVAL_MODE_LABEL, type RetrievalMode } from "@/features/rag/types";
import { formatDateTimeValue } from "@/lib/date-utils";
import { createIdempotencyKey } from "@/lib/idempotency-key";
import {
  DocumentScopePicker,
  type DocumentSelection,
} from "./document-scope-picker";
import { ListPagination, type ListPagingProps } from "./list-pagination";
import { SearchEvidenceResults } from "./search-evidence";

const NO_PROVIDER_VALUE = "__none__";

function formatIndexStatus(status: string): {
  label: string;
  variant: "default" | "secondary" | "outline" | "warning" | "destructive";
} {
  switch (status) {
    case "completed":
      return { label: "Hoàn tất", variant: "default" };
    case "failed":
      return { label: "Thất bại", variant: "destructive" };
    case "cancelled":
      return { label: "Đã hủy", variant: "outline" };
    case "running":
      return { label: "Đang dựng", variant: "secondary" };
    case "dispatched":
      return { label: "Đã gửi worker", variant: "secondary" };
    default:
      return { label: status, variant: "outline" };
  }
}

/**
 * Index generations and a source-bearing search test.
 *
 * Everything shown comes from the real endpoints: no fabricated generation, no
 * optimistic "indexed" badge, and a failed run keeps its error code.
 */
type IndexPanelProps = ListPagingProps & {
  workspaceId: string;
  collectionId: string;
  canManage: boolean;
  role?: CallerWorkspaceRole;
};

export function IndexPanel(props: IndexPanelProps) {
  const { sessionId } = useSyncExternalStore(
    subscribeToken,
    getTokenState,
    getTokenState,
  );
  return (
    <IndexSession
      key={JSON.stringify([sessionId, props.workspaceId, props.collectionId])}
      {...props}
    />
  );
}

function IndexSession({
  workspaceId,
  collectionId,
  canManage,
  role,
  page = 1,
  pageSize = 20,
  onPageChange,
  onPageSizeChange,
}: IndexPanelProps) {
  const runsQuery = useIndexRunsQuery(workspaceId, collectionId, {
    page,
    pageSize,
  });
  const catalogQuery = useCatalogQuery(workspaceId);
  const requestMutation = useRequestIndexMutation(workspaceId, collectionId);
  const searchMutation = useSearchMutation(workspaceId, collectionId);

  const embeddingCatalog = (catalogQuery.data ?? []).filter((item) =>
    item.capabilities.includes("embedding"),
  );
  const rerankCatalog = (catalogQuery.data ?? []).filter((item) =>
    item.capabilities.includes("rerank"),
  );

  const [providerId, setProviderId] = useState<string>(NO_PROVIDER_VALUE);
  const [contextualSearch, setContextualSearch] = useState(false);
  const [catalogScope, setCatalogScope] = useState(false);
  const [requestKey, setRequestKey] = useState(() => createIdempotencyKey());

  const [query, setQuery] = useState("");
  const [selectedDocuments, setSelectedDocuments] = useState<
    DocumentSelection[]
  >([]);
  const [mode, setMode] = useState<RetrievalMode>(DEFAULT_SEARCH_INPUT.mode);
  const [topK, setTopK] = useState(DEFAULT_SEARCH_INPUT.top_k);
  const [candidateK, setCandidateK] = useState(
    DEFAULT_SEARCH_INPUT.candidate_k,
  );
  const [rrfK, setRrfK] = useState(DEFAULT_SEARCH_INPUT.rrf_k);
  const [rerankProviderId, setRerankProviderId] = useState<string | null>(null);
  const [filterDraft, setFilterDraft] = useState<MetadataFilterDraft>(
    EMPTY_METADATA_FILTER_DRAFT,
  );
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);
  const hasFilterErrors =
    Object.keys(validateMetadataFilterDraft(filterDraft)).length > 0;
  const mountedRef = useRef(true);
  const searchAttemptRef = useRef(0);
  const sessionAtMount = useRef(getTokenState().sessionId).current;

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const isCurrentSession = () =>
    mountedRef.current && getTokenState().sessionId === sessionAtMount;

  const runs = (runsQuery.data ?? []).slice(0, pageSize);
  const activeRun = useMemo(() => runs.find((run) => run.is_active), [runs]);
  const latestRun = runs[0];

  const handleRequestIndex = async () => {
    try {
      const outcome = await requestMutation.mutateAsync({
        providerId: providerId === NO_PROVIDER_VALUE ? null : providerId,
        idempotencyKey: requestKey,
        contextualSearch,
      });
      if (!isCurrentSession()) return;
      if (outcome.created) {
        toast.success(
          outcome.dispatched
            ? `Đã tạo và gửi index generation #${outcome.run.generation}.`
            : `Đã tạo index generation #${outcome.run.generation}, đang chờ worker.`,
        );
        // A new intent needs a new key; a retry of the same intent reuses it.
        setRequestKey(createIdempotencyKey());
      } else {
        toast.info(
          `Yêu cầu này đã được xử lý trước đó: generation #${outcome.run.generation} (${outcome.run.status}).`,
        );
      }
    } catch (error) {
      if (!isCurrentSession()) return;
      if (error instanceof ApiProblemError) {
        toast.error(error.message);
      } else {
        toast.error("Không tạo được index generation.");
      }
    }
  };

  const handleSearch = async () => {
    if (hasFilterErrors) {
      setResult(null);
      setSearchError("Hãy sửa năm trong phạm vi metadata trước khi tìm kiếm.");
      return;
    }
    const trimmed = query.trim();
    if (!trimmed) {
      toast.error("Nhập câu truy vấn để tìm thử.");
      return;
    }
    if (mode !== "dense" && candidateK < topK) {
      toast.error(
        "Ngân sách ứng viên phải lớn hơn hoặc bằng Top K khi dùng hybrid hoặc rerank.",
      );
      return;
    }
    const attempt = ++searchAttemptRef.current;
    setSearchError(null);
    setResult(null);
    try {
      const response = await searchMutation.mutateAsync({
        query: trimmed,
        document_ids: selectedDocuments.length
          ? selectedDocuments.map((d) => d.id)
          : null,
        top_k: topK,
        mode,
        candidate_k: candidateK,
        rrf_k: rrfK,
        rerank_provider_id: mode === "hybrid_rerank" ? rerankProviderId : null,
        metadata_filter: draftToFilter(filterDraft),
        scope_resolution: catalogScope ? "catalog" : "explicit",
      });
      if (!isCurrentSession() || searchAttemptRef.current !== attempt) return;
      setResult(response);
    } catch (error) {
      if (!isCurrentSession() || searchAttemptRef.current !== attempt) return;
      setResult(null);
      setSearchError(
        error instanceof ApiProblemError
          ? error.message
          : "Không tìm được kết quả từ bộ sưu tập.",
      );
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-2.5 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-sm font-semibold text-foreground">
            Chỉ mục &amp; Tìm kiếm
          </h2>
          <p className="text-xs text-muted-foreground">
            Mỗi generation đánh chỉ mục các bản đã xuất bản. Chỉ generation đang
            hoạt động mới phục vụ trả lời.
          </p>
        </div>

        {canManage ? (
          <div className="flex flex-wrap items-end gap-2">
            <Field className="w-full">
              <FieldLabel htmlFor="index-contextual" className="text-xs">
                <Checkbox
                  id="index-contextual"
                  checked={contextualSearch}
                  disabled={requestMutation.isPending}
                  onCheckedChange={(value) => {
                    setContextualSearch(value === true);
                    setRequestKey(createIdempotencyKey());
                  }}
                />
                Gắn ngữ cảnh có nguồn cho chỉ mục mới
              </FieldLabel>
              <FieldDescription className="text-xs">
                Chỉ mục mới sẽ thay bản đang hoạt động sau khi hoàn tất.
              </FieldDescription>
            </Field>
            <div className="w-[200px]">
              <FieldLabel htmlFor="index-provider" className="text-[11px]">
                Provider embedding
              </FieldLabel>
              <Select
                value={providerId}
                onValueChange={setProviderId}
                disabled={catalogQuery.isPending}
              >
                <SelectTrigger
                  id="index-provider"
                  className="h-8 text-xs"
                  aria-label="Provider embedding"
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={NO_PROVIDER_VALUE} className="text-xs">
                    Theo mặc định workspace
                  </SelectItem>
                  {embeddingCatalog.map((item) => (
                    <SelectItem
                      key={item.id}
                      value={item.id}
                      className="text-xs"
                    >
                      {item.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button
              size="sm"
              className="h-8 text-xs gap-1.5"
              disabled={requestMutation.isPending}
              onClick={() => void handleRequestIndex()}
            >
              {requestMutation.isPending ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Play className="size-3.5" />
              )}
              <span>Tạo index generation</span>
            </Button>
          </div>
        ) : null}
      </div>

      {runsQuery.isPending ? (
        <Skeleton className="h-24 w-full rounded-xl" />
      ) : runsQuery.isError ? (
        <Alert variant="destructive" className="py-3">
          <AlertCircle className="size-4" />
          <AlertTitle className="text-xs">
            Không đọc được danh sách index generation
          </AlertTitle>
          <AlertDescription className="text-xs">
            <p>
              {runsQuery.error instanceof Error
                ? runsQuery.error.message
                : "Lỗi không xác định."}
            </p>
            <Button
              size="sm"
              variant="outline"
              className="mt-2 h-7 text-xs gap-1.5"
              onClick={() => void runsQuery.refetch()}
            >
              <RefreshCw className="size-3" />
              Thử lại
            </Button>
          </AlertDescription>
        </Alert>
      ) : runs.length === 0 ? (
        <Card className="rounded-xl border-dashed">
          <CardContent className="p-6 text-center text-xs text-muted-foreground">
            <Database className="mx-auto mb-2 size-6 text-muted-foreground/70" />
            <p className="font-semibold text-foreground">
              Không có index generation trong trang này
            </p>
            <p className="mt-1">
              Xuất bản ít nhất một phiên bản tài liệu, sau đó tạo index
              generation để trợ lý có thể trả lời.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {!activeRun ? (
            <Alert className="border-warning/40 bg-warning/10 py-2.5 text-xs">
              <AlertCircle className="size-3.5 text-warning" />
              <AlertDescription className="text-[11px]">
                Chưa thấy generation đang phục vụ trong trang này. Chỉ
                generation đã hoàn tất và được kích hoạt mới phục vụ trả lời.
              </AlertDescription>
            </Alert>
          ) : null}

          <div className="overflow-x-auto rounded-xl border">
            <table className="w-full text-xs">
              <thead className="bg-muted/40 text-[11px] uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="px-3 py-2 text-left font-semibold">Gen</th>
                  <th className="px-3 py-2 text-left font-semibold">
                    Trạng thái
                  </th>
                  <th className="px-3 py-2 text-left font-semibold">Chunks</th>
                  <th className="px-3 py-2 text-left font-semibold">
                    Provider
                  </th>
                  <th className="px-3 py-2 text-left font-semibold">
                    Yêu cầu lúc
                  </th>
                  <th className="px-3 py-2 text-left font-semibold">Quản lý</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {runs.map((run) => (
                  <IndexRunRow
                    key={run.id}
                    run={run}
                    workspaceId={workspaceId}
                    role={role}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <ListPagination
        page={page}
        pageSize={pageSize}
        onPageChange={onPageChange}
        onPageSizeChange={onPageSizeChange}
        hasNext={(runsQuery.data?.length ?? 0) > pageSize}
        disabled={runsQuery.isFetching}
        label="chỉ mục"
      />
      {/* Search test */}
      <Card className="rounded-xl shadow-2xs">
        <CardContent className="space-y-3 p-3 sm:p-4">
          <div className="flex items-center gap-2">
            <Search className="size-3.5 text-primary" />
            <span className="text-xs font-semibold text-foreground">
              Tìm kiếm thử
            </span>
            {latestRun ? (
              <Badge variant="outline" className="font-mono text-[10px] py-0">
                gen #{latestRun.generation}
              </Badge>
            ) : null}
          </div>

          <div className="flex flex-col gap-2 sm:flex-row">
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Nhập câu hỏi hoặc từ khóa để kiểm tra nội dung đã đánh chỉ mục..."
              className="text-xs"
              aria-label="Câu truy vấn tìm kiếm thử"
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  void handleSearch();
                }
              }}
            />
            <Button
              size="sm"
              className="h-9 shrink-0 text-xs gap-1.5"
              disabled={searchMutation.isPending || hasFilterErrors}
              onClick={() => void handleSearch()}
            >
              {searchMutation.isPending ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Search className="size-3.5" />
              )}
              <span>Tìm thử</span>
            </Button>
          </div>

          <DocumentScopePicker
            workspaceId={workspaceId}
            collectionId={collectionId}
            selected={selectedDocuments}
            onChange={(documents) => {
              setSelectedDocuments(documents);
              ++searchAttemptRef.current;
              setResult(null);
              setSearchError(null);
            }}
          />
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Field>
              <FieldLabel htmlFor="search-mode" className="text-[11px]">
                Chế độ
              </FieldLabel>
              <Select
                value={mode}
                onValueChange={(value) => setMode(value as RetrievalMode)}
              >
                <SelectTrigger
                  id="search-mode"
                  className="h-8 text-xs"
                  aria-label="Chế độ truy xuất"
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(Object.keys(RETRIEVAL_MODE_LABEL) as RetrievalMode[]).map(
                    (item) => (
                      <SelectItem key={item} value={item} className="text-xs">
                        {RETRIEVAL_MODE_LABEL[item]}
                      </SelectItem>
                    ),
                  )}
                </SelectContent>
              </Select>
            </Field>

            <Field>
              <FieldLabel htmlFor="search-topk" className="text-[11px]">
                Top K
              </FieldLabel>
              <Input
                id="search-topk"
                type="number"
                min={1}
                max={50}
                value={topK}
                onChange={(event) =>
                  setTopK(
                    event.target.value === "" ? 5 : Number(event.target.value),
                  )
                }
                className="h-8 text-xs"
              />
            </Field>

            {mode !== "dense" ? (
              <>
                <Field>
                  <FieldLabel
                    htmlFor="search-candidates"
                    className="text-[11px]"
                  >
                    Ứng viên
                  </FieldLabel>
                  <Input
                    id="search-candidates"
                    type="number"
                    min={1}
                    max={100}
                    value={candidateK}
                    onChange={(event) =>
                      setCandidateK(
                        event.target.value === ""
                          ? 30
                          : Number(event.target.value),
                      )
                    }
                    className="h-8 text-xs"
                  />
                </Field>
                <Field>
                  <FieldLabel htmlFor="search-rrf" className="text-[11px]">
                    RRF k
                  </FieldLabel>
                  <Input
                    id="search-rrf"
                    type="number"
                    min={1}
                    max={1000}
                    value={rrfK}
                    onChange={(event) =>
                      setRrfK(
                        event.target.value === ""
                          ? 60
                          : Number(event.target.value),
                      )
                    }
                    className="h-8 text-xs"
                  />
                </Field>
              </>
            ) : null}
          </div>

          {mode === "hybrid_rerank" ? (
            <Field>
              <FieldLabel htmlFor="search-rerank" className="text-[11px]">
                Provider rerank
              </FieldLabel>
              <Select
                value={rerankProviderId ?? NO_PROVIDER_VALUE}
                onValueChange={(value) =>
                  setRerankProviderId(
                    value === NO_PROVIDER_VALUE ? null : value,
                  )
                }
              >
                <SelectTrigger
                  id="search-rerank"
                  className="h-8 text-xs"
                  aria-label="Provider rerank"
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={NO_PROVIDER_VALUE} className="text-xs">
                    Không dùng rerank
                  </SelectItem>
                  {rerankCatalog.map((item) => (
                    <SelectItem
                      key={item.id}
                      value={item.id}
                      className="text-xs"
                    >
                      {item.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FieldDescription className="text-[11px]">
                Điểm rerank là thang riêng, không cộng trực tiếp với điểm vector
                và không phải xác suất trả lời đúng.
              </FieldDescription>
            </Field>
          ) : null}

          <div className="space-y-2 border-t pt-3">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Phạm vi metadata
            </p>
            <FieldLabel htmlFor="search-catalog-scope" className="text-xs">
              <Checkbox
                id="search-catalog-scope"
                checked={catalogScope}
                onCheckedChange={(value) => setCatalogScope(value === true)}
              />
              Nhận diện phạm vi từ câu hỏi; yêu cầu làm rõ khi mơ hồ
            </FieldLabel>
            <MetadataFilterFields
              value={filterDraft}
              onChange={setFilterDraft}
              columns={3}
              showHint={false}
            />
            <p className="text-[11px] text-muted-foreground">
              Bộ lọc áp dụng trước Top K. Nội dung chưa được gắn metadata sẽ
              không khớp bộ lọc có giá trị cụ thể.
            </p>
          </div>

          {searchError ? (
            <Alert variant="destructive" className="py-2.5">
              <AlertCircle className="size-3.5" />
              <AlertDescription className="text-[11px]">
                {searchError}
              </AlertDescription>
            </Alert>
          ) : null}

          {result ? (
            <SearchEvidenceResults
              key={`${result.index_run_id}:${JSON.stringify(result.hits.map((h) => h.chunk_id))}`}
              result={result}
              workspaceId={workspaceId}
              collectionId={collectionId}
            />
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}

function IndexRunRow({
  run,
  workspaceId,
  role,
}: {
  run: IndexRun;
  workspaceId: string;
  role?: CallerWorkspaceRole;
}) {
  const status = formatIndexStatus(run.status);
  const active = isActiveStatus(run.status);

  return (
    <tr className="align-top">
      <td className="px-3 py-2">
        <div className="flex items-center gap-1.5">
          <span className="font-mono font-semibold">#{run.generation}</span>
          {run.is_active ? (
            <Badge variant="default" className="text-[10px] py-0 gap-0.5">
              <CheckCircle2 className="size-2.5" />
              active
            </Badge>
          ) : null}
        </div>
      </td>
      <td className="px-3 py-2">
        <div className="flex items-center gap-1.5">
          <Badge variant={status.variant} className="text-[10px] py-0">
            {status.label}
          </Badge>
          {active ? (
            <Loader2 className="size-3 animate-spin text-primary" />
          ) : null}
        </div>
        {run.error_code ? (
          <p className="mt-1 font-mono text-[10px] text-destructive">
            {run.error_code}
          </p>
        ) : null}
      </td>
      <td className="px-3 py-2 font-mono text-[11px]">{run.chunks_total}</td>
      <td className="px-3 py-2 font-mono text-[11px] text-muted-foreground">
        {run.provider_id}
      </td>
      <td className="px-3 py-2 text-[11px] text-muted-foreground">
        {formatDateTimeValue(run.requested_at)}
      </td>
      <td className="px-3 py-2">
        {!active && !run.is_active ? (
          <LifecycleActions
            workspaceId={workspaceId}
            kind="index"
            resourceId={run.id}
            label={`Chỉ mục #${run.generation}`}
            role={role}
          />
        ) : null}
      </td>
    </tr>
  );
}

function isActiveStatus(status: string): boolean {
  return (
    status !== "completed" && status !== "failed" && status !== "cancelled"
  );
}
