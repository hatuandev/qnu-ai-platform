import { Button } from "@/components/ui/button";

export type AnswerCoverage = {
  status: "complete" | "partial" | "insufficient" | "not_assessed";
  requirements: {
    label: string;
    status: "covered" | "missing" | "conflicting";
    evidence_ids: string[];
  }[];
  structures: {
    label: string;
    required_units: number;
    provided_units: number;
    cited_units: number;
    status: "covered" | "partial";
    uncovered_evidence_ids?: string[];
  }[];
  basis: string;
  scope_status?: "bounded" | "unresolved" | "not_requested";
};

export function AnswerCoverageNotice({
  coverage,
  onOpenSources,
}: {
  coverage?: AnswerCoverage | null;
  onOpenSources?: (ids: string[]) => void;
}) {
  if (!coverage || !["partial", "insufficient"].includes(coverage.status))
    return null;
  const missing = coverage.requirements.filter(
    (item) => item.status !== "covered",
  );
  const incomplete = coverage.structures.filter(
    (item) => item.status === "partial",
  );
  const evidenceIds = [
    ...new Set([
      ...missing.flatMap((item) => item.evidence_ids),
      ...incomplete.flatMap((item) => item.uncovered_evidence_ids ?? []),
    ]),
  ];
  if (
    !missing.length &&
    !incomplete.length &&
    coverage.scope_status !== "unresolved"
  )
    return null;
  return (
    <div role="note" className="border-t pt-3 space-y-1.5 text-sm">
      <p className="font-medium text-warning">
        {coverage.status === "partial"
          ? "Câu trả lời mới bao quát một phần yêu cầu"
          : "Nội dung còn thiếu căn cứ"}
      </p>
      {missing.map((item) => (
        <p key={item.label} className="text-muted-foreground break-words">
          {item.status === "conflicting"
            ? "Cần đối chiếu nguồn mâu thuẫn"
            : "Chưa giải đáp đủ"}
          : {item.label}
        </p>
      ))}
      {incomplete.map((item) => (
        <p key={item.label} className="text-muted-foreground break-words">
          Chưa bao quát hết nội dung của {item.label}. Cần xem thêm nguồn trước
          khi coi đây là danh sách đầy đủ.
        </p>
      ))}
      {coverage.scope_status === "unresolved" && (
        <p className="text-muted-foreground">
          Chưa xác định được phạm vi nguồn đầy đủ cho yêu cầu liệt kê. Các ý có
          dẫn chứng chỉ phản ánh phần đã tìm được.
        </p>
      )}
      {evidenceIds.length > 0 && onOpenSources && (
        <Button
          variant="link"
          size="sm"
          className="px-0"
          onClick={() => onOpenSources(evidenceIds)}
        >
          Xem nguồn cần đối chiếu
        </Button>
      )}
    </div>
  );
}
