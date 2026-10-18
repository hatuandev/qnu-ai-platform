import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Field } from "@/components/admin/field";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { knowledgeApi } from "@/services/knowledge-api";
import type {
  CleanContentPreview,
  ContentIntegrityIssue,
} from "@/types/knowledge";
import type { StudioOCRDocument, StudioOCRPage } from "@/types/studio-ocr";
import { changedLines, locateIssueOffset } from "../utils/clean-content";

interface Props {
  collectionId: string;
  sourceId: string;
  doc: StudioOCRDocument;
  page: StudioOCRPage;
  draft: string;
  pageDraft: string;
  hasEdits: boolean;
  disabled: boolean;
  reason: string;
  onReasonChange: (value: string) => void;
  onChange: (value: string) => void;
  onApply: (markdown: string) => void;
  onLocate: (issue: ContentIntegrityIssue) => void;
}

export function CleanContentReview(props: Props) {
  const { doc, page, draft, disabled } = props;
  const [preview, setPreview] = useState<{
    input: string;
    result: CleanContentPreview;
  }>();
  const [isChecking, setIsChecking] = useState(false);
  const [selectedIssue, setSelectedIssue] = useState<ContentIntegrityIssue>();
  const editor = useRef<HTMLTextAreaElement>(null);
  const latest = useRef(draft);
  latest.current = draft;
  const isCurrent = preview?.input === draft;
  const report = isCurrent
    ? preview.result.report
    : !props.hasEdits
      ? doc.contentIntegrity
      : undefined;
  const changes = changedLines(page.markdown, props.pageDraft);
  useEffect(() => {
    if (!selectedIssue) return;
    const offset = locateIssueOffset(
      draft,
      props.pageDraft,
      page.pageNumber,
      selectedIssue,
    );
    if (offset === null) return;
    editor.current?.focus();
    const end = props.pageDraft.indexOf("\n", offset);
    editor.current?.setSelectionRange(
      offset,
      end < 0 ? props.pageDraft.length : end,
    );
  }, [selectedIssue, draft, props.pageDraft, page.pageNumber]);
  const handleCheck = async () => {
    if (!doc.revisionId) return;
    setIsChecking(true);
    try {
      const result = await knowledgeApi.previewCleanContent(
        props.collectionId,
        props.sourceId,
        doc.revisionId,
        draft,
        doc.canonicalHash,
      );
      if (latest.current !== draft)
        throw new Error(
          "Nội dung đã đổi trong lúc kiểm tra; hãy kiểm tra lại.",
        );
      setPreview({ input: draft, result });
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "Không kiểm tra được nội dung.",
      );
    } finally {
      setIsChecking(false);
    }
  };
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-auto rounded-lg border border-border bg-card p-3 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold">Đối chiếu bản sạch</h3>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={disabled || isChecking || !doc.revisionId}
            onClick={handleCheck}
          >
            {isChecking ? "Đang kiểm tra…" : "Kiểm tra"}
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={
              disabled ||
              !isCurrent ||
              preview.result.canonical_markdown === draft
            }
            onClick={() =>
              preview && props.onApply(preview.result.canonical_markdown)
            }
          >
            Áp dụng đề xuất
          </Button>
        </div>
      </div>
      <p className="text-xs text-muted-foreground">
        Chỉ chuẩn hóa hình thức, không tự sửa OCR/số/năm. Kiểm tra là heuristic,
        không chứng nhận nội dung đúng. Lưu → Duyệt → Nạp vector → Xuất bản là
        các bước riêng.
      </p>
      {doc.paginationKnown === false && (
        <p className="text-xs text-warning">
          Chưa xác minh trang vật lý. Số phần hiển thị trong Studio không phải
          căn cứ trích dẫn số trang.
        </p>
      )}
      <Field
        label="Lý do hiệu đính hoặc ghi chú duyệt"
        htmlFor="content-review-reason"
      >
        <Textarea
          id="content-review-reason"
          value={props.reason}
          onChange={(e) => props.onReasonChange(e.target.value)}
          maxLength={2000}
          disabled={disabled}
          rows={2}
          placeholder="Đã đối chiếu phần nào, sửa gì và vì sao…"
        />
      </Field>
      {doc.contentReview?.actor_id && (
        <p className="text-xs text-muted-foreground">
          Lần sửa đã lưu: {doc.contentReview.actor_id} ·{" "}
          {doc.contentReview.reason} · {doc.contentReview.at}
        </p>
      )}
      <details open>
        <summary className="cursor-pointer font-medium">
          Kiểm tra toàn vẹn
        </summary>
        {!report ? (
          <p className="py-2 text-muted-foreground">
            Bản nháp chưa được kiểm tra lại.
          </p>
        ) : (
          <>
            {isCurrent && (
              <p className="text-xs text-muted-foreground">
                Kết quả cho bản đề xuất; chưa áp dụng hoặc lưu.
              </p>
            )}
            <p className="py-2 text-xs text-muted-foreground">
              {report.issues.length
                ? `${report.issues.length} điểm cần xem`
                : "Chưa phát hiện vấn đề bằng các kiểm tra hiện có; vẫn cần đối chiếu nguồn."}
            </p>
            <div className="max-h-48 space-y-1 overflow-auto">
              {report.issues.map((issue) => (
                <Button
                  key={issue.id}
                  variant="ghost"
                  className="h-auto w-full justify-start whitespace-normal text-left text-sm"
                  onClick={() => {
                    setSelectedIssue(issue);
                    props.onLocate(issue);
                  }}
                >
                  {issue.page_number
                    ? `Trang ${issue.page_number} · `
                    : "Chưa rõ trang · "}
                  {issue.line_number
                    ? `Dòng ${issue.line_number}`
                    : "Vị trí dòng chưa xác định"}
                  : {issue.message}
                </Button>
              ))}
            </div>
          </>
        )}
      </details>
      <details>
        <summary className="cursor-pointer font-medium">
          Text bóc tách ban đầu
        </summary>
        <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-words py-2 text-sm">
          {page.rawTextAvailable
            ? page.rawText
            : "Bản cũ chưa lưu text bóc tách độc lập. Đối chiếu tệp nguồn; không coi Markdown hiện tại là text gốc."}
        </pre>
      </details>
      {isCurrent && preview.result.canonical_markdown !== draft && (
        <details>
          <summary className="cursor-pointer font-medium">
            Xem bản đề xuất trước khi áp dụng
          </summary>
          <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-words text-sm">
            {preview.result.canonical_markdown}
          </pre>
        </details>
      )}
      <Field label="Bản sạch đang sửa" htmlFor="clean-page-markdown">
        <Textarea
          id="clean-page-markdown"
          ref={editor}
          value={props.pageDraft}
          onChange={(e) => props.onChange(e.target.value)}
          disabled={disabled || isChecking}
          className="min-h-64 font-mono text-sm"
        />
      </Field>
      <details>
        <summary className="cursor-pointer font-medium">
          So với revision đang mở ({changes.length} dòng khác)
        </summary>
        <p className="text-xs text-muted-foreground">
          Đối chiếu cùng số dòng, không phải căn chỉnh ngữ nghĩa. Lưu bản sửa
          không ghi đè revision này.
        </p>
        <div className="max-h-64 overflow-auto">
          {changes.map((line) => (
            <div
              key={line.id}
              className="grid grid-cols-1 gap-2 border-b border-border py-2 md:grid-cols-2"
            >
              <pre className="whitespace-pre-wrap break-words text-sm">
                <span className="text-muted-foreground">
                  Trước · dòng {line.id}:{" "}
                </span>
                {line.before}
              </pre>
              <pre className="whitespace-pre-wrap break-words text-sm">
                <span className="text-primary">Sau · dòng {line.id}: </span>
                {line.after}
              </pre>
            </div>
          ))}
        </div>
      </details>
    </div>
  );
}
