import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { useState } from "react";
import { z } from "zod";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import { ErrorState } from "@/components/admin/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { EvidenceFields } from "./evidence-fields";
import type { SearchHit, SearchResponse } from "./index-types";
import { getPublishedCompiledDocument } from "./publication-requests";
import { SourceTablesView } from "./source-tables-view";

const rowsSchema = z.array(
  z.array(
    z.object({
      text: z.string(),
      header: z.boolean(),
      row_span: z.number().int().positive(),
      col_span: z.number().int().positive(),
    }),
  ),
);
export function hitTitle(hit: SearchHit) {
  const context = hit.structure?.context;
  if (
    context &&
    typeof context === "object" &&
    "title" in context &&
    typeof context.title === "string"
  )
    return context.title;
  const namedSource = Object.values(hit.citations).find(
    (value) =>
      value &&
      typeof value === "object" &&
      "filename" in value &&
      typeof value.filename === "string",
  );
  if (
    namedSource &&
    typeof namedSource === "object" &&
    "filename" in namedSource &&
    typeof namedSource.filename === "string"
  )
    return namedSource.filename;
  return hit.kind === "table" ? "Bảng nguồn" : "Trích đoạn tài liệu";
}
export function EvidenceChunk({ hit }: { hit: SearchHit }) {
  const rows = rowsSchema.safeParse(hit.structure?.rows);
  return (
    <div className="space-y-4">
      {!rows.success ? (
        <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">
          {hit.text}
        </p>
      ) : null}
      {rows.success ? (
        <SourceTablesView
          tables={[
            {
              citation:
                typeof hit.structure?.source_table_citation === "string"
                  ? hit.structure.source_table_citation
                  : hit.chunk_id,
              page_number: Object.values(hit.citations)
                .map((v) =>
                  v && typeof v === "object" && "page_number" in v
                    ? v.page_number
                    : undefined,
                )
                .find((v): v is number => typeof v === "number"),
              table: { rows: rows.data },
            },
          ]}
        />
      ) : null}
      <section className="space-y-2">
        <h3 className="text-sm font-semibold">Metadata và cấu trúc</h3>
        <EvidenceFields
          value={
            hit.structure
              ? {
                  context: hit.structure.context ?? null,
                  retrieval_metadata: hit.structure.retrieval_metadata ?? null,
                  page_notes: hit.structure.page_notes ?? null,
                }
              : null
          }
        />
        {rows.success ? (
          <details>
            <summary className="cursor-pointer text-xs text-muted-foreground">
              Văn bản đoạn nguyên trạng
            </summary>
            <p className="whitespace-pre-wrap break-words text-sm pt-2">
              {hit.text}
            </p>
          </details>
        ) : null}
      </section>
      <section className="space-y-2">
        <h3 className="text-sm font-semibold">Nguồn trích dẫn</h3>
        <EvidenceFields value={hit.citations} />
      </section>
    </div>
  );
}
export function SearchEvidenceSheet({
  workspaceId,
  collectionId,
  hit,
  onClose,
}: {
  workspaceId: string;
  collectionId: string;
  hit: SearchHit;
  onClose: () => void;
}) {
  const { sessionId } = useV1Auth();
  const publication = useQuery({
    queryKey: [
      "v1",
      sessionId,
      "search-publication",
      workspaceId,
      collectionId,
      hit.document_id,
      hit.version_id,
      hit.publication_decision_id,
    ],
    queryFn: ({ signal }) =>
      getPublishedCompiledDocument(
        v1Client,
        workspaceId,
        collectionId,
        hit.document_id,
        { signal },
      ),
    retry: false,
    staleTime: 0,
    refetchInterval: 5000,
  });
  const matches =
    publication.data?.version.id === hit.version_id &&
    publication.data?.decision.id === hit.publication_decision_id;
  return (
    <Sheet
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <SheetContent
        side="right"
        className="p-0 flex flex-col w-full max-w-full sm:max-w-2xl"
      >
        <SheetHeader className="p-4 pr-14 border-b bg-muted/20">
          <SheetTitle>{hitTitle(hit)}</SheetTitle>
          <SheetDescription>
            Đối chiếu trích đoạn với đúng phiên bản và quyết định xuất bản tại
            thời điểm tìm kiếm.
          </SheetDescription>
        </SheetHeader>
        <div className="p-4 min-h-0 flex-1 overflow-y-auto space-y-4">
          {publication.isPending ? (
            <p role="status">Đang kiểm tra nguồn đang phục vụ…</p>
          ) : publication.isError ? (
            <ErrorState
              error={publication.error}
              onRetry={() => void publication.refetch()}
            />
          ) : !matches ? (
            <p role="alert" className="text-sm text-warning">
              Nguồn đã thay đổi hoặc bị thu hồi. Hãy tìm kiếm lại để lấy bằng
              chứng hiện hành.
            </p>
          ) : (
            <>
              <div className="text-xs text-muted-foreground space-y-1 break-all">
                <p>Đoạn: {hit.chunk_id}</p>
                <p>Phiên bản: {hit.version_id}</p>
                <p>Quyết định: {hit.publication_decision_id}</p>
                <p>
                  Điểm xếp hạng: {hit.score} · {hit.kind}
                </p>
              </div>
              <EvidenceChunk hit={hit} />
              <EvidenceSourceLinks
                workspaceId={workspaceId}
                collectionId={collectionId}
                hit={hit}
              />
              <Button variant="outline" size="sm" asChild>
                <Link
                  to="/workspaces/$workspaceId/collections/$collectionId/documents/$documentId/versions/$versionId"
                  params={{
                    workspaceId,
                    collectionId,
                    documentId: hit.document_id,
                    versionId: hit.version_id,
                  }}
                >
                  Mở phiên bản nguồn
                </Link>
              </Button>
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
function EvidenceSourceLinks({
  workspaceId,
  collectionId,
  hit,
}: {
  workspaceId: string;
  collectionId: string;
  hit: SearchHit;
}) {
  const schema = z.object({
    workspace_id: z.literal(workspaceId),
    collection_id: z.literal(collectionId),
    source_id: z.string().min(1).max(64),
    revision_id: z.string().min(1).max(64),
    filename: z.string(),
    page_number: z.number().int().positive().optional(),
  });
  return (
    <div className="flex flex-wrap gap-2">
      {Object.entries(hit.citations).map(([id, value]) => {
        const parsed = schema.safeParse(value);
        if (!parsed.success) return null;
        const citation = parsed.data;
        const runId = id.split(":")[0];
        if (!runId || runId.length > 64) return null;
        return (
          <Button
            key={id}
            asChild
            variant="outline"
            size="sm"
            className="h-auto min-h-9 max-w-full whitespace-normal break-all text-left"
          >
            <Link
              to="/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId"
              params={{
                workspaceId,
                collectionId,
                sourceId: citation.source_id,
              }}
              search={{
                revisionId: citation.revision_id,
                runId,
                page: citation.page_number,
                tab: "ocr",
                subTab: "artifacts",
              }}
            >
              Mở OCR · {citation.filename}
              {citation.page_number ? ` · Trang ${citation.page_number}` : ""}
            </Link>
          </Button>
        );
      })}
    </div>
  );
}
export function SearchEvidenceResults({
  result,
  workspaceId,
  collectionId,
}: {
  result: SearchResponse;
  workspaceId: string;
  collectionId: string;
}) {
  const [selected, setSelected] = useState<SearchHit | null>(null);
  return (
    <div className="space-y-3 border-t pt-3">
      <div className="flex flex-wrap gap-2 text-sm">
        <Badge variant="outline">Chỉ mục #{result.generation}</Badge>
        <span>
          {result.hits.length} kết quả · {result.eligible_documents} tài liệu đủ
          điều kiện
        </span>
      </div>
      {result.hits.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Không có đoạn nào khớp. Bộ lọc metadata không được nới tự động.
        </p>
      ) : (
        <ol className="space-y-3">
          {result.hits.map((hit) => (
            <li key={hit.chunk_id} className="rounded-lg border p-3 space-y-2">
              <h3 className="text-sm font-semibold">{hitTitle(hit)}</h3>
              <p className="text-xs text-muted-foreground">
                {hit.kind} · Điểm xếp hạng {hit.score.toFixed(4)}
              </p>
              <p className="line-clamp-4 whitespace-pre-wrap text-sm">
                {hit.text}
              </p>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setSelected(hit)}
              >
                Xem đoạn và nguồn
              </Button>
            </li>
          ))}
        </ol>
      )}
      {result.skipped_documents.length ? (
        <details className="text-sm">
          <summary className="cursor-pointer font-medium">
            Tài liệu bị bỏ qua ({result.skipped_documents.length})
          </summary>
          <div className="pt-3">
            <EvidenceFields value={result.skipped_documents} />
          </div>
        </details>
      ) : null}
      <details className="text-sm">
        <summary className="cursor-pointer font-medium">
          Chi tiết xếp hạng và phạm vi
        </summary>
        <div className="pt-3">
          <EvidenceFields value={result.trace} />
        </div>
      </details>
      <p className="text-xs text-muted-foreground">
        Điểm ở các thang khác nhau không cộng trực tiếp và không phải xác suất
        câu trả lời đúng. Kết quả truy xuất chưa đánh giá chất lượng câu trả
        lời.
      </p>
      {selected ? (
        <SearchEvidenceSheet
          key={selected.chunk_id}
          workspaceId={workspaceId}
          collectionId={collectionId}
          hit={selected}
          onClose={() => setSelected(null)}
        />
      ) : null}
    </div>
  );
}
