import { AlertCircle, Plus, Quote, Trash2 } from "lucide-react";
import { useId } from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import type {
  MetadataEvidence,
  MetadataValues,
  RetrievalAnnotation,
} from "@/features/rag/types";
import { describeAnnotationTarget } from "@/features/rag/types";

/**
 * Declares `retrieval_metadata` for a compiled version.
 *
 * The backend validates every value against the pinned source bytes
 * (`qnu/domains/knowledge/metadata.py`): the target must exist in the compiled
 * draft, each declared value must literally appear in one of the supplied
 * quotes, and `document` targets may only carry `issued_year` and the effective
 * interval. This editor mirrors those rules so the operator sees the problem
 * before the request, but the backend stays the authority — nothing here infers
 * a value from a file name or from the document title.
 */
export type AnnotationTargetKind = "document" | "paragraph" | "table";

export type AnnotationDraft = {
  /** Local React key only; never sent. */
  id: string;
  targetKind: AnnotationTargetKind;
  /** `paragraph:s:p` indices, as typed. */
  section: string;
  paragraph: string;
  /** `table:citation:row:r[:column:c]` parts, as typed. */
  citation: string;
  row: string;
  column: string;
  dataYear: string;
  issuedYear: string;
  effectiveFrom: string;
  effectiveUntil: string;
  program: string;
  intake: string;
  attributeName?: string;
  attributeValue?: string;
  attributeType?: "text" | "number" | "boolean";
  /** Evidence rows carry a local id so editing keeps React state stable. */
  evidence: { id: string; citation: string; quote: string }[];
};

let draftCounter = 0;
let evidenceCounter = 0;

function nextEvidenceId(): string {
  evidenceCounter += 1;
  return `evidence-${evidenceCounter}`;
}

export function emptyAnnotationDraft(
  targetKind: AnnotationTargetKind = "document",
): AnnotationDraft {
  draftCounter += 1;
  return {
    id: `annotation-${draftCounter}`,
    targetKind,
    section: "",
    paragraph: "",
    citation: "",
    row: "",
    column: "",
    dataYear: "",
    issuedYear: "",
    effectiveFrom: "",
    effectiveUntil: "",
    program: "",
    intake: "",
    evidence: [{ id: nextEvidenceId(), citation: "", quote: "" }],
  };
}

function parseInteger(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  if (!/^\d+$/.test(trimmed)) return null;
  return Number(trimmed);
}

function parseYear(value: string): number | null {
  const parsed = parseInteger(value);
  if (parsed === null) return null;
  if (parsed < 1000 || parsed > 9999) return null;
  return parsed;
}

/** Composes the exact target string the backend expects. */
export function draftTarget(draft: AnnotationDraft): string {
  if (draft.targetKind === "document") return "document";
  if (draft.targetKind === "paragraph") {
    const section = parseInteger(draft.section);
    const paragraph = parseInteger(draft.paragraph);
    if (section === null || paragraph === null) return "";
    return `paragraph:${section}:${paragraph}`;
  }
  const citation = draft.citation.trim();
  const row = parseInteger(draft.row);
  if (!citation || row === null) return "";
  const column = parseInteger(draft.column);
  return column === null
    ? `table:${citation}:row:${row}`
    : `table:${citation}:row:${row}:column:${column}`;
}

function draftValues(draft: AnnotationDraft): MetadataValues {
  const values: MetadataValues = {};
  const dataYear = parseYear(draft.dataYear);
  if (dataYear !== null) values.data_year = dataYear;
  const issuedYear = parseYear(draft.issuedYear);
  if (issuedYear !== null) values.issued_year = issuedYear;
  if (draft.effectiveFrom) values.effective_from = draft.effectiveFrom;
  if (draft.effectiveUntil) values.effective_until = draft.effectiveUntil;
  if (draft.program.trim()) values.program = draft.program.trim();
  if (draft.intake.trim()) values.intake = draft.intake.trim();
  const label = draft.attributeName?.trim();
  const raw = draft.attributeValue?.trim();
  if (label && raw) {
    if (draft.attributeType === "number" && Number.isFinite(Number(raw))) {
      values.attributes = { [label]: Number(raw) };
    } else if (draft.attributeType === "boolean") {
      if (raw === "true" || raw === "false")
        values.attributes = { [label]: raw === "true" };
    } else if (draft.attributeType !== "number") {
      values.attributes = { [label]: raw };
    }
  }
  return values;
}

function draftEvidence(draft: AnnotationDraft): MetadataEvidence[] {
  return draft.evidence
    .map((item) => ({
      citation: item.citation.trim(),
      quote: item.quote.trim(),
    }))
    .filter((item) => item.citation.length > 0 && item.quote.length > 0);
}

/**
 * Problems that block submission, in the order the operator should fix them.
 * Mirrors the backend validators that can be checked without the draft bytes.
 */
export function annotationDraftIssues(
  drafts: AnnotationDraft[],
): Map<string, string[]> {
  const issues = new Map<string, string[]>();
  const seenTargets = new Map<string, number>();

  for (const draft of drafts) {
    const list: string[] = [];
    const target = draftTarget(draft);

    if (!target) {
      list.push(
        draft.targetKind === "paragraph"
          ? "Cần nhập chỉ số mục và đoạn (bắt đầu từ 0)."
          : "Cần nhập mã dẫn chứng và chỉ số hàng (bắt đầu từ 0).",
      );
    } else {
      const previous = seenTargets.get(target);
      if (previous !== undefined) {
        list.push(
          `Trùng target với mục ${previous + 1}. Gộp các trường vào một mục.`,
        );
      } else {
        seenTargets.set(target, drafts.indexOf(draft));
      }
    }

    const values = draftValues(draft);
    if (
      (draft.attributeName?.trim() || draft.attributeValue?.trim()) &&
      !values.attributes
    ) {
      list.push("Cần tên và giá trị hợp lệ cho thuộc tính bổ sung.");
    }
    if (Object.keys(values).length === 0) {
      list.push("Cần khai báo ít nhất một giá trị metadata.");
    }

    if (target === "document") {
      if (values.data_year !== undefined) {
        list.push(
          "Target toàn tài liệu không nhận Năm dữ liệu; hãy gắn vào đoạn hoặc hàng/ô cụ thể.",
        );
      }
      if (values.program !== undefined) {
        list.push(
          "Target toàn tài liệu không nhận Ngành; hãy gắn vào đoạn hoặc hàng/ô cụ thể.",
        );
      }
      if (values.intake !== undefined) {
        list.push(
          "Target toàn tài liệu không nhận Đợt; hãy gắn vào đoạn hoặc hàng/ô cụ thể.",
        );
      }
    }

    if (
      values.effective_from &&
      values.effective_until &&
      values.effective_from > values.effective_until
    ) {
      list.push("Ngày bắt đầu hiệu lực phải trước hoặc bằng ngày kết thúc.");
    }

    const evidence = draftEvidence(draft);
    if (evidence.length === 0) {
      list.push("Cần ít nhất một trích đoạn nguồn (dẫn chứng + câu trích).");
    }
    for (const item of evidence) {
      if (item.citation.length < 3 || item.citation.length > 200) {
        list.push("Mã dẫn chứng phải dài từ 3 đến 200 ký tự.");
      }
      if (item.quote.length > 2000) {
        list.push("Câu trích tối đa 2000 ký tự.");
      }
    }

    if (list.length > 0) issues.set(draft.id, list);
  }

  return issues;
}

/** Drops incomplete drafts; returns only what the backend can validate. */
export function draftsToAnnotations(
  drafts: AnnotationDraft[],
): RetrievalAnnotation[] {
  return drafts.map((draft) => ({
    target: draftTarget(draft),
    values: draftValues(draft),
    evidence: draftEvidence(draft),
  }));
}

export function RetrievalMetadataEditor({
  drafts,
  onChange,
  disabled,
}: {
  drafts: AnnotationDraft[];
  onChange: (next: AnnotationDraft[]) => void;
  disabled?: boolean;
}) {
  const issues = annotationDraftIssues(drafts);

  const patch = (id: string, part: Partial<AnnotationDraft>) => {
    onChange(
      drafts.map((draft) => (draft.id === id ? { ...draft, ...part } : draft)),
    );
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="space-y-0.5">
          <Label className="text-xs font-semibold text-foreground">
            Metadata truy xuất
          </Label>
          <p className="text-[11px] text-muted-foreground max-w-lg">
            Khai báo có căn cứ cho từng giá trị. Bỏ trống nếu chưa xác định —
            không suy đoán từ tên tệp hay tiêu đề.
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="h-7 gap-1 text-[11px]"
          disabled={disabled}
          onClick={() => onChange([...drafts, emptyAnnotationDraft()])}
        >
          <Plus className="size-3" />
          Thêm metadata
        </Button>
      </div>

      {drafts.length === 0 ? (
        <p className="rounded-md border border-dashed bg-muted/20 px-3 py-2.5 text-[11px] text-muted-foreground">
          Chưa khai báo metadata. Phiên bản vẫn đăng ký được, nhưng tìm kiếm có
          lọc theo năm/ngành/đợt sẽ không trả về tài liệu này.
        </p>
      ) : null}

      {drafts.map((draft, index) => (
        <AnnotationCard
          key={draft.id}
          draft={draft}
          index={index}
          issues={issues.get(draft.id) ?? []}
          disabled={disabled}
          onPatch={(part) => patch(draft.id, part)}
          onRemove={() =>
            onChange(drafts.filter((item) => item.id !== draft.id))
          }
        />
      ))}
    </div>
  );
}

function AnnotationCard({
  draft,
  index,
  issues,
  disabled,
  onPatch,
  onRemove,
}: {
  draft: AnnotationDraft;
  index: number;
  issues: string[];
  disabled?: boolean;
  onPatch: (part: Partial<AnnotationDraft>) => void;
  onRemove: () => void;
}) {
  const targetId = useId();
  const sectionId = useId();
  const paragraphId = useId();
  const citationId = useId();
  const rowId = useId();
  const columnId = useId();
  const dataYearId = useId();
  const issuedYearId = useId();
  const effectiveFromId = useId();
  const effectiveUntilId = useId();
  const programId = useId();
  const intakeId = useId();
  const attributeNameId = useId();
  const attributeValueId = useId();

  const target = draftTarget(draft);
  const isDocumentTarget = draft.targetKind === "document";

  const patchEvidence = (
    evidenceIndex: number,
    part: Partial<{ citation: string; quote: string }>,
  ) => {
    onPatch({
      evidence: draft.evidence.map((item, i) =>
        i === evidenceIndex ? { ...item, ...part } : item,
      ),
    });
  };
  return (
    <div className="rounded-lg border bg-card p-3 space-y-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-xs font-semibold text-foreground">
            Metadata #{index + 1}
          </p>
          <p className="text-[11px] text-muted-foreground font-mono truncate">
            {target
              ? `${describeAnnotationTarget(target)}`
              : "Chưa đủ thông tin target"}
          </p>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="size-7 text-muted-foreground hover:text-destructive"
          disabled={disabled}
          onClick={onRemove}
          aria-label={`Xoá metadata #${index + 1}`}
        >
          <Trash2 className="size-3.5" />
        </Button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="space-y-1">
          <Label htmlFor={targetId} className="text-[11px]">
            Gắn vào
          </Label>
          <Select
            value={draft.targetKind}
            disabled={disabled}
            onValueChange={(value) =>
              onPatch({ targetKind: value as AnnotationTargetKind })
            }
          >
            <SelectTrigger id={targetId} className="h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="document" className="text-xs">
                Toàn tài liệu (chỉ 1 nguồn)
              </SelectItem>
              <SelectItem value="paragraph" className="text-xs">
                Đoạn văn cụ thể
              </SelectItem>
              <SelectItem value="table" className="text-xs">
                Hàng/ô bảng cụ thể
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        {draft.targetKind === "paragraph" ? (
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1">
              <Label htmlFor={sectionId} className="text-[11px]">
                Mục (0…)
              </Label>
              <Input
                id={sectionId}
                inputMode="numeric"
                value={draft.section}
                disabled={disabled}
                onChange={(e) => onPatch({ section: e.target.value })}
                className="h-8 text-xs"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor={paragraphId} className="text-[11px]">
                Đoạn (0…)
              </Label>
              <Input
                id={paragraphId}
                inputMode="numeric"
                value={draft.paragraph}
                disabled={disabled}
                onChange={(e) => onPatch({ paragraph: e.target.value })}
                className="h-8 text-xs"
              />
            </div>
          </div>
        ) : null}

        {draft.targetKind === "table" ? (
          <div className="grid grid-cols-3 gap-2">
            <div className="space-y-1 col-span-3">
              <Label htmlFor={citationId} className="text-[11px]">
                Mã dẫn chứng bảng
              </Label>
              <Input
                id={citationId}
                value={draft.citation}
                disabled={disabled}
                placeholder="ocr-…:ev-…"
                onChange={(e) => onPatch({ citation: e.target.value })}
                className="h-8 text-xs font-mono"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor={rowId} className="text-[11px]">
                Hàng (0…)
              </Label>
              <Input
                id={rowId}
                inputMode="numeric"
                value={draft.row}
                disabled={disabled}
                onChange={(e) => onPatch({ row: e.target.value })}
                className="h-8 text-xs"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor={columnId} className="text-[11px]">
                Cột (tuỳ chọn)
              </Label>
              <Input
                id={columnId}
                inputMode="numeric"
                value={draft.column}
                disabled={disabled}
                onChange={(e) => onPatch({ column: e.target.value })}
                className="h-8 text-xs"
              />
            </div>
          </div>
        ) : null}
      </div>

      <div className="grid gap-2 sm:grid-cols-3">
        <label htmlFor={attributeNameId} className="space-y-1 text-xs">
          Tên thuộc tính
          <Input
            id={attributeNameId}
            value={draft.attributeName ?? ""}
            disabled={disabled}
            maxLength={80}
            onChange={(e) => onPatch({ attributeName: e.target.value })}
          />
        </label>
        <div className="space-y-1 text-xs">
          <span>Kiểu giá trị</span>
          <Select
            value={draft.attributeType ?? "text"}
            disabled={disabled}
            onValueChange={(value) =>
              onPatch({
                attributeType: value as AnnotationDraft["attributeType"],
                attributeValue: "",
              })
            }
          >
            <SelectTrigger aria-label="Kiểu giá trị">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="text">Văn bản</SelectItem>
              <SelectItem value="number">Số</SelectItem>
              <SelectItem value="boolean">True / False</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <label htmlFor={attributeValueId} className="space-y-1 text-xs">
          Giá trị
          <Input
            id={attributeValueId}
            value={draft.attributeValue ?? ""}
            disabled={disabled}
            maxLength={500}
            onChange={(e) => onPatch({ attributeValue: e.target.value })}
          />
        </label>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 border-t pt-3">
        {!isDocumentTarget ? (
          <div className="space-y-1">
            <Label htmlFor={dataYearId} className="text-[11px]">
              Năm dữ liệu
            </Label>
            <Input
              id={dataYearId}
              inputMode="numeric"
              placeholder="Để trống nếu chưa xác định"
              value={draft.dataYear}
              disabled={disabled}
              onChange={(e) => onPatch({ dataYear: e.target.value })}
              className="h-8 text-xs"
            />
          </div>
        ) : null}

        <div className="space-y-1">
          <Label htmlFor={issuedYearId} className="text-[11px]">
            Năm ban hành
          </Label>
          <Input
            id={issuedYearId}
            inputMode="numeric"
            placeholder="Để trống nếu chưa xác định"
            value={draft.issuedYear}
            disabled={disabled}
            onChange={(e) => onPatch({ issuedYear: e.target.value })}
            className="h-8 text-xs"
          />
        </div>

        <div className="space-y-1">
          <Label htmlFor={effectiveFromId} className="text-[11px]">
            Hiệu lực từ ngày
          </Label>
          <Input
            id={effectiveFromId}
            type="date"
            value={draft.effectiveFrom}
            disabled={disabled}
            onChange={(e) => onPatch({ effectiveFrom: e.target.value })}
            className="h-8 text-xs"
          />
        </div>

        <div className="space-y-1">
          <Label htmlFor={effectiveUntilId} className="text-[11px]">
            Hiệu lực đến ngày
          </Label>
          <Input
            id={effectiveUntilId}
            type="date"
            value={draft.effectiveUntil}
            disabled={disabled}
            onChange={(e) => onPatch({ effectiveUntil: e.target.value })}
            className="h-8 text-xs"
          />
        </div>

        {!isDocumentTarget ? (
          <>
            <div className="space-y-1">
              <Label htmlFor={programId} className="text-[11px]">
                Ngành
              </Label>
              <Input
                id={programId}
                maxLength={160}
                value={draft.program}
                disabled={disabled}
                onChange={(e) => onPatch({ program: e.target.value })}
                className="h-8 text-xs"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor={intakeId} className="text-[11px]">
                Đợt
              </Label>
              <Input
                id={intakeId}
                maxLength={160}
                value={draft.intake}
                disabled={disabled}
                onChange={(e) => onPatch({ intake: e.target.value })}
                className="h-8 text-xs"
              />
            </div>
          </>
        ) : null}
      </div>

      <div className="space-y-2 border-t pt-3">
        <div className="flex items-center justify-between">
          <Label className="text-[11px] flex items-center gap-1.5">
            <Quote className="size-3" />
            Trích đoạn nguồn chứng minh
          </Label>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-6 px-1.5 text-[11px]"
            disabled={disabled}
            onClick={() =>
              onPatch({
                evidence: [
                  ...draft.evidence,
                  { id: nextEvidenceId(), citation: "", quote: "" },
                ],
              })
            }
          >
            <Plus className="size-3" />
            Thêm trích đoạn
          </Button>
        </div>

        {draft.evidence.map((item, evidenceIndex) => (
          <div key={item.id} className="space-y-1.5 rounded-md bg-muted/20 p-2">
            <div className="flex items-center gap-2">
              <Input
                value={item.citation}
                disabled={disabled}
                placeholder="Mã dẫn chứng (citation)"
                onChange={(e) =>
                  patchEvidence(evidenceIndex, { citation: e.target.value })
                }
                className="h-7 text-[11px] font-mono flex-1"
                aria-label={`Mã dẫn chứng ${evidenceIndex + 1}`}
              />
              {draft.evidence.length > 1 ? (
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="size-7 text-muted-foreground hover:text-destructive"
                  disabled={disabled}
                  onClick={() =>
                    onPatch({
                      evidence: draft.evidence.filter(
                        (_, i) => i !== evidenceIndex,
                      ),
                    })
                  }
                  aria-label={`Xoá trích đoạn ${evidenceIndex + 1}`}
                >
                  <Trash2 className="size-3" />
                </Button>
              ) : null}
            </div>
            <Textarea
              value={item.quote}
              disabled={disabled}
              placeholder="Câu trích nguyên văn chứa giá trị đã khai báo"
              rows={2}
              maxLength={2000}
              onChange={(e) =>
                patchEvidence(evidenceIndex, { quote: e.target.value })
              }
              className="text-[11px] resize-none"
              aria-label={`Câu trích ${evidenceIndex + 1}`}
            />
          </div>
        ))}
      </div>

      {issues.length > 0 ? (
        <Alert variant="destructive" className="py-2">
          <AlertCircle className="size-4" />
          <AlertDescription className="text-[11px]">
            <ul className="list-disc pl-3.5 space-y-0.5">
              {issues.map((issue) => (
                <li key={issue}>{issue}</li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      ) : null}
    </div>
  );
}
