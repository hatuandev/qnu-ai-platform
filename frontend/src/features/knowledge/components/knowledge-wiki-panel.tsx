import { useQuery } from "@tanstack/react-query";
import { BookOpen, RefreshCw } from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { useRbac } from "@/rbac/context";
import { extractErrorMessage, knowledgeApi } from "@/services/knowledge-api";
import type {
  KnowledgeWikiPage,
  KnowledgeWikiReference,
  KnowledgeWikiResponse,
} from "@/types/knowledge-wiki";
import { KnowledgeWikiNavigation } from "./knowledge-wiki-navigation";

const kindLabels = { source: "Nguồn", entity: "Đối tượng", concept: "Chủ đề" };

function WikiArticle({ page }: { page: KnowledgeWikiPage }) {
  const [reference, setReference] = useState<KnowledgeWikiReference | null>(
    null,
  );
  return (
    <>
      <div className="prose prose-sm dark:prose-invert max-w-none overflow-x-auto">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            img: () => null,
            a: ({ href, children }) => {
              const ref = page.references.find(
                (item) => href === `#source-${item.unit_id}`,
              );
              return ref ? (
                <Button
                  variant="link"
                  size="sm"
                  onClick={() => setReference(ref)}
                >
                  Xem nguồn
                </Button>
              ) : (
                <span>{children}</span>
              );
            },
          }}
        >
          {page.markdown.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, "")}
        </ReactMarkdown>
      </div>
      <Sheet
        open={reference !== null}
        onOpenChange={(open) => {
          if (!open) setReference(null);
        }}
      >
        <SheetContent className="overflow-y-auto">
          <SheetHeader>
            <SheetTitle>Trích đoạn nguồn</SheetTitle>
            <SheetDescription>
              {reference?.page_number
                ? `Trang ${reference.page_number}`
                : "Nội dung trong bản nguồn đang xem"}
            </SheetDescription>
          </SheetHeader>
          <p className="p-4 whitespace-pre-wrap text-sm">{reference?.quote}</p>
        </SheetContent>
      </Sheet>
    </>
  );
}

export function KnowledgeWikiContent({
  data,
}: {
  data: KnowledgeWikiResponse;
}) {
  if (data.status !== "ready" || data.pages.length === 0)
    return (
      <p className="text-sm text-muted-foreground">
        {data.status === "unavailable"
          ? "Chưa biên soạn được trang tri thức. Bản nguồn chuẩn vẫn được giữ nguyên để tra cứu."
          : data.status === "pending"
            ? "Trang tri thức được biên soạn tự động khi nạp vector cho bản nguồn mới."
            : "Bản nguồn này chưa có trang tri thức. Các nội dung đã nạp được giữ nguyên."}
      </p>
    );
  return (
    <>
      <p className="text-sm text-muted-foreground">
        Nội dung được biên soạn theo chủ đề. Bấm Xem nguồn để đối chiếu; phạm vi
        năm, điều kiện và ngoại lệ được giữ trong từng phần.
      </p>
      <Accordion type="single" collapsible defaultValue={data.pages[0]?.id}>
        {data.pages.map((page) => (
          <AccordionItem key={page.id} value={page.id} id={`wiki-${page.id}`}>
            <AccordionTrigger>
              <span className="flex flex-wrap items-center gap-2 text-left">
                <Badge variant="secondary">{kindLabels[page.kind]}</Badge>
                {page.title}
              </span>
            </AccordionTrigger>
            <AccordionContent>
              <WikiArticle page={page} />
            </AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </>
  );
}

export function KnowledgeWikiPanel({
  collectionId,
  sourceId,
  revisionId,
}: {
  collectionId: string;
  sourceId: string;
  revisionId: string;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const rbac = useRbac();
  const canRead =
    rbac.isAccessVerified && !rbac.isDemoMode && rbac.can("ai.knowledge.view");
  const query = useQuery({
    queryKey: ["knowledge-source-pages", collectionId, sourceId, revisionId],
    queryFn: () =>
      knowledgeApi.getSourceKnowledgePages(collectionId, sourceId, revisionId),
    enabled: isOpen && canRead,
  });
  if (!canRead) return null;
  return (
    <Card className="rounded-xl shadow-2xs">
      <CardHeader className="flex flex-row items-center justify-between gap-2 p-4">
        <CardTitle className="flex items-center gap-2 text-sm">
          <BookOpen className="size-4" />
          Trang tri thức
        </CardTitle>
        <Button
          size="sm"
          variant="outline"
          className="text-xs"
          aria-expanded={isOpen}
          onClick={() => setIsOpen(!isOpen)}
        >
          {isOpen ? "Thu gọn" : "Xem trang"}
        </Button>
      </CardHeader>
      {isOpen && (
        <CardContent className="space-y-3 px-4 pb-4">
          {query.isLoading && (
            <p role="status" className="text-sm text-muted-foreground">
              Đang tải trang tri thức…
            </p>
          )}
          {query.isError && (
            <Alert variant="destructive">
              <AlertDescription>
                {extractErrorMessage(
                  query.error,
                  "Không đọc được trang tri thức.",
                )}
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => query.refetch()}
                >
                  <RefreshCw className="size-3.5" />
                  Thử lại
                </Button>
              </AlertDescription>
            </Alert>
          )}
          {query.data && <KnowledgeWikiContent data={query.data} />}
          {query.data?.source_revision_no && (
            <p className="text-xs text-muted-foreground">
              Đang xem bản nguồn {query.data.source_revision_no}
            </p>
          )}
          <KnowledgeWikiNavigation
            collectionId={collectionId}
            sourceId={sourceId}
            revisionId={revisionId}
            canReview={rbac.can("ai.knowledge.review")}
          />
        </CardContent>
      )}
    </Card>
  );
}
