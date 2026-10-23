import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { extractErrorMessage, knowledgeApi } from "@/services/knowledge-api";
import type {
  KnowledgeWikiMap,
  KnowledgeWikiNode,
} from "@/types/knowledge-wiki";

const yearLabels = {
  data: "Dữ liệu",
  publication: "Ban hành",
  effective: "Hiệu lực",
  event: "Sự kiện",
};

export function relatedWikiPages(
  data: KnowledgeWikiMap,
  bindingId: string,
  revisionId: string,
): KnowledgeWikiNode[] {
  const own = new Set(
    data.pages
      .filter(
        (p) =>
          p.binding_id === bindingId && p.source_revision_id === revisionId,
      )
      .map((p) => p.id),
  );
  const ids = new Set(
    data.graph.links
      .filter(
        (link) =>
          link.status === "structural" &&
          (own.has(link.source) || own.has(link.target)),
      )
      .flatMap((link) => [link.source, link.target]),
  );
  return data.pages.filter((p) => ids.has(p.id) && p.binding_id !== bindingId);
}

export function WikiRelatedLinks({
  data,
  bindingId,
  revisionId,
}: {
  data: KnowledgeWikiMap;
  bindingId: string;
  revisionId: string;
}) {
  const pages = relatedWikiPages(data, bindingId, revisionId);
  return (
    <div className="space-y-2">
      <p className="text-sm font-medium">Trang liên quan và liên kết ngược</p>
      {pages.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Chưa có trang liên quan trong phạm vi đang phục vụ.
        </p>
      ) : (
        <>
          <p className="text-xs text-muted-foreground">
            Các nguồn cùng nhắc đến tên này. Mỗi trích đoạn giữ phạm vi riêng;
            cùng tên chưa chứng minh cùng đối tượng.
          </p>
          <ul className="space-y-2">
            {pages.map((page) => (
              <li key={page.id} className="space-y-1">
                <Button
                  asChild
                  variant="link"
                  size="sm"
                  className="h-auto max-w-full whitespace-normal p-0 text-left"
                >
                  <a
                    href={`/knowledge/${encodeURIComponent(data.collection_id)}/sources/${encodeURIComponent(page.binding_id)}?revision=${encodeURIComponent(page.source_revision_id)}#wiki-${encodeURIComponent(page.id)}`}
                  >
                    {page.title}
                  </a>
                </Button>
                <p className="text-xs text-muted-foreground break-words">
                  {page.source_title} · Bản {page.source_revision_no}
                </p>
                <p className="text-xs text-muted-foreground">
                  {page.temporal.length
                    ? Array.from(
                        new Set(
                          page.temporal.map(
                            (scope) =>
                              `${yearLabels[scope.role]}: ${scope.years.join(", ")}`,
                          ),
                        ),
                      ).join(" · ")
                    : "Phạm vi năm chưa xác định"}
                </p>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

export function KnowledgeWikiNavigation({
  collectionId,
  sourceId,
  revisionId,
  canReview,
}: {
  collectionId: string;
  sourceId: string;
  revisionId: string;
  canReview: boolean;
}) {
  const [isReviewOpen, setIsReviewOpen] = useState(false);
  const map = useQuery({
    queryKey: ["knowledge-map", collectionId],
    queryFn: () => knowledgeApi.getKnowledgeMap(collectionId),
  });
  const review = useQuery({
    queryKey: ["knowledge-wiki-review", collectionId, sourceId, revisionId],
    queryFn: () =>
      knowledgeApi.getSourceKnowledgeReview(collectionId, sourceId, revisionId),
    enabled: canReview && isReviewOpen,
  });
  const relations = useQuery({
    queryKey: ["knowledge-map-review", collectionId],
    queryFn: () => knowledgeApi.getKnowledgeMap(collectionId, true),
    enabled: canReview && isReviewOpen,
  });
  const issues = [
    ...(review.data?.issues ?? []),
    ...(relations.data?.issues ?? []),
  ];
  return (
    <div className="space-y-3 border-t pt-3">
      {map.isLoading && (
        <p role="status" className="text-sm text-muted-foreground">
          Đang tải trang liên quan…
        </p>
      )}
      {map.isError && (
        <Alert>
          <AlertDescription>
            {extractErrorMessage(map.error, "Không đọc được trang liên quan.")}
            <Button size="sm" variant="ghost" onClick={() => map.refetch()}>
              Thử lại
            </Button>
          </AlertDescription>
        </Alert>
      )}
      {map.data && !map.isError && !map.isFetching && (
        <WikiRelatedLinks
          data={map.data}
          bindingId={sourceId}
          revisionId={revisionId}
        />
      )}
      {canReview && (
        <>
          <Button
            size="sm"
            variant="outline"
            aria-expanded={isReviewOpen}
            onClick={() => setIsReviewOpen(!isReviewOpen)}
          >
            Đối chiếu nâng cao
          </Button>
          {isReviewOpen && (
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground">
                Kết quả chỉ để đối chiếu, không tự sửa dữ kiện hoặc thay đổi
                quyền xuất bản.
              </p>
              {(review.isLoading || relations.isLoading) && (
                <p role="status" className="text-sm">
                  Đang đối chiếu…
                </p>
              )}
              {(review.isError || relations.isError) && (
                <Alert variant="destructive">
                  <AlertDescription>
                    {extractErrorMessage(
                      review.error ?? relations.error,
                      "Không đọc được kết quả đối chiếu.",
                    )}
                  </AlertDescription>
                </Alert>
              )}
              {review.isSuccess &&
                relations.isSuccess &&
                issues.length === 0 && (
                  <p className="text-sm">
                    Chưa phát hiện vấn đề trong các kiểm tra cấu trúc hiện có.
                  </p>
                )}
              <ul className="space-y-2">
                {Array.from(
                  new Map(
                    (review.isError || relations.isError ? [] : issues).map(
                      (item) => [item.id, item],
                    ),
                  ).values(),
                ).map((item) => (
                  <li key={item.id} className="text-sm">
                    <Badge
                      variant={
                        item.category === "blocker"
                          ? "destructive"
                          : "secondary"
                      }
                    >
                      {
                        {
                          blocker: "Cần xử lý",
                          warning: "Cần đối chiếu",
                          source_limitation: "Giới hạn nguồn",
                          candidate: "Gợi ý chưa xác minh",
                          provider_infrastructure: "Lỗi biên soạn",
                          stale: "Chưa sẵn sàng",
                        }[item.category]
                      }
                    </Badge>{" "}
                    {item.message}
                    <p className="text-xs text-muted-foreground break-all">
                      {item.code}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </div>
  );
}
