import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type {
  ContextIssueDecision,
  ContextReviewIssue,
  SemanticEvidenceBinding,
  SourceArtifact,
} from "@/types/knowledge";

const stateLabels = {
  not_stated: "Nguồn chưa nêu / chưa công bố",
  not_applicable: "Không áp dụng",
  ambiguous: "Chưa rõ nghĩa",
  unreadable: "Chưa đọc được",
};
const scopeLabels = {
  table: "Toàn bảng",
  row: "Một dòng",
  group: "Nhóm dòng",
  column: "Cột cụ thể",
};

function rowLabel(table: SourceArtifact["tables"][number], row: string) {
  const index = table.row_unit_ids?.indexOf(row) ?? -1;
  return index < 0
    ? "Dòng không còn tồn tại"
    : table.rows[index]?.slice(0, 3).filter(Boolean).join(" · ");
}

function EvidenceReviewDetails({
  binding,
  reason,
  sourceText,
}: {
  binding?: SemanticEvidenceBinding | null;
  reason?: string | null;
  sourceText?: string;
}) {
  return (
    <div className="space-y-1 break-words text-muted-foreground">
      {reason && <p>Lý do đề xuất: {reason}</p>}
      {binding && (
        <p className="break-all text-xs">
          Đơn vị nguồn: {binding.source_unit_id} · khoảng ký tự Unicode [
          {binding.start}, {binding.end}) trong{" "}
          {binding.coordinate_space === "cell_raw_codepoints"
            ? "giá trị gốc của ô"
            : "đơn vị nguồn"}{" "}
          · hash {binding.text_sha256.slice(0, 12)}. Trích đoạn do backend lấy
          nguyên văn; quan hệ vẫn cần bạn đối chiếu.
        </p>
      )}
      {binding && (
        <details>
          <summary>Đọc toàn bộ đơn vị nguồn và điều kiện loại trừ</summary>
          <SourceEvidenceLink binding={binding} />
          {!sourceText && (
            <p>Không tải được đơn vị nguồn; chưa đủ căn cứ đối chiếu.</p>
          )}
        </details>
      )}
    </div>
  );
}

function ContextIssueItem({
  issue,
  artifact,
  onDecision,
  selected,
}: {
  issue: ContextReviewIssue;
  artifact: SourceArtifact;
  onDecision?: (decision: ContextIssueDecision | null, issueId: string) => void;
  selected?: boolean;
}) {
  const [reason, setReason] = useState("");
  const assessment =
    artifact.semantic_annotations?.context_review?.reference_assessments?.find(
      (item) => item.issue_id === issue.issue_id,
    );
  const review = artifact.semantic_annotations?.context_review;
  const label = review?.display_labels?.issues?.[issue.issue_id];
  const evidence = assessment?.evidence.length
    ? issue.review_evidence?.[0]
    : issue.review_evidence?.find(
        (item) => !item.evidence_quote.trimStart().startsWith("#"),
      );
  const action =
    !evidence || assessment?.relevance === "insufficient"
      ? null
      : assessment?.relevance === "related"
        ? "related_context_reviewed"
        : issue.kind === "scope_confirmation_required"
          ? "scope_confirmed"
          : issue.kind === "deferred_reference"
            ? "not_applicable_to_target"
            : null;
  const rows = Array.isArray(issue.target.row_unit_ids)
    ? issue.target.row_unit_ids
    : [];
  const columns = Array.isArray(issue.target.column_ids)
    ? issue.target.column_ids
    : [];
  const tableIds = Array.isArray(issue.target.table_ids)
    ? issue.target.table_ids
    : [issue.target.table_id];
  return (
    <article className="space-y-2 rounded-lg border p-3">
      <p className="font-medium">
        {label && `${label} · `}
        {issue.reason}
      </p>
      <p className="text-muted-foreground">
        {selected
          ? "Đã chọn đối chiếu, chưa gửi quyết định"
          : assessment?.relevance === "insufficient"
            ? "Còn thiếu bằng chứng"
            : "Chờ quyết định có xác thực"}
      </p>
      {artifact.tables
        .filter((table) => tableIds.includes(table.id))
        .map((table) => (
          <div key={table.id} className="space-y-1 break-words">
            <p>Bảng {artifact.tables.indexOf(table) + 1}</p>
            {rows.length > 0 && (
              <p>
                Dòng cần xác nhận:{" "}
                {rows.map((row) => rowLabel(table, row)).join("; ")}
              </p>
            )}
            {columns.length > 0 && (
              <p>
                Cột cần xác nhận:{" "}
                {columns
                  .map(
                    (id) =>
                      table.columns
                        ?.find((column) => column.id === id)
                        ?.header_path.join(" / ") ?? "Cột không còn tồn tại",
                  )
                  .join("; ")}
              </p>
            )}
          </div>
        ))}
      <details className="break-all text-muted-foreground">
        <summary>Thông tin truy vết phạm vi và nguồn</summary>
        <p>
          {JSON.stringify(issue.target)} · {issue.unit_ids.join(", ")}
        </p>
      </details>
      {issue.review_evidence?.map((item) => (
        <SourceEvidenceLink
          key={item.evidence_binding.evidence_id}
          binding={item.evidence_binding}
        />
      ))}
      {assessment && (
        <div className="space-y-2">
          <p>Phân tích tham chiếu cần bạn đối chiếu: {assessment.reason}</p>
          {assessment.links?.map((link) => (
            <div
              key={link.assertion_id}
              className="space-y-1 rounded-md border p-2"
            >
              <p>
                {review?.display_labels?.assertions?.[link.assertion_id] ??
                  link.assertion_id}{" "}
                ·{" "}
                {link.role === "direct"
                  ? "Trực tiếp (direct)"
                  : link.role === "protective"
                    ? "Bảo vệ (protective)"
                    : "Có điều kiện (conditional)"}
              </p>
              <p>{link.reason}</p>
              {link.condition && <p>Chỉ khi: {link.condition}</p>}
              {link.evidence.map((item) => (
                <SourceEvidenceLink
                  key={item.evidence_binding.evidence_id}
                  binding={item.evidence_binding}
                />
              ))}
            </div>
          ))}
          {assessment.evidence.map((item) => (
            <SourceEvidenceLink
              key={item.evidence_binding.evidence_id}
              binding={item.evidence_binding}
            />
          ))}
        </div>
      )}
      {!action && (
        <p>
          Cần bổ sung và phân tích lại nguồn; ghi chú chung không giải quyết
          được vấn đề này.
        </p>
      )}
      {action && evidence && onDecision && (
        <>
          <Textarea
            aria-label={`Căn cứ quyết định ${issue.issue_id}`}
            value={reason}
            onChange={(event) => {
              setReason(event.target.value);
              if (selected) onDecision(null, issue.issue_id);
            }}
            placeholder="Ghi căn cứ đối chiếu toàn đơn vị nguồn và đúng phạm vi đích"
          />
          <Button
            type="button"
            variant="outline"
            disabled={reason.trim().length < 3}
            onClick={() =>
              onDecision(
                selected
                  ? null
                  : {
                      issue_id: issue.issue_id,
                      target: issue.target,
                      action,
                      ...evidence,
                      reason: reason.trim(),
                      supporting_evidence: assessment?.evidence.map(
                        (item) => item.evidence_binding,
                      ),
                    },
                issue.issue_id,
              )
            }
          >
            {selected
              ? "Bỏ lựa chọn đối chiếu"
              : action === "scope_confirmed"
                ? "Xác nhận đúng tập dòng/cột này"
                : action === "related_context_reviewed"
                  ? "Xác nhận đã đối chiếu tham chiếu liên quan"
                  : "Xác nhận tham chiếu không chi phối đích này"}
          </Button>
        </>
      )}
    </article>
  );
}

function SemanticReviewContent({
  artifact,
  decisions = [],
  onDecision,
}: {
  artifact: SourceArtifact;
  decisions?: ContextIssueDecision[];
  onDecision?: (decision: ContextIssueDecision | null, issueId: string) => void;
}) {
  const proposal = artifact.semantic_annotations;
  const contextPanel = proposal?.context_review && (
    <section
      aria-label="Vấn đề ngữ cảnh và lịch sử đối chiếu"
      className="space-y-3 text-sm"
    >
      <p className="font-medium">
        Ngữ cảnh và phạm vi · trạng thái: {proposal.status}
      </p>
      <p>
        Phạm vi:{" "}
        {proposal.context_review.scope === "selected_tables"
          ? "các bảng được chọn"
          : "tài liệu"}
        . {artifact.source_policy?.context_blocker_count ?? 0} vấn đề còn chặn
        áp dụng/xuất bản.
      </p>
      {[
        {
          title: "Vấn đề gốc và tham chiếu",
          items: (proposal.context_review.issues ?? []).filter(
            (issue) =>
              !proposal.context_review?.display_labels?.issues?.[
                issue.issue_id
              ]?.startsWith("S"),
          ),
        },
        {
          title: "Xác nhận phạm vi của từng quan hệ",
          items: (proposal.context_review.issues ?? []).filter((issue) =>
            proposal.context_review?.display_labels?.issues?.[
              issue.issue_id
            ]?.startsWith("S"),
          ),
        },
      ]
        .filter((group) => group.items.length > 0)
        .map((group) => (
          <section key={group.title} className="space-y-3">
            <p className="font-medium">
              {group.title} ({group.items.length})
            </p>
            {group.items.map((issue) => (
              <ContextIssueItem
                key={issue.issue_id}
                issue={issue}
                artifact={artifact}
                selected={decisions.some(
                  (item) => item.issue_id === issue.issue_id,
                )}
                onDecision={
                  proposal.status === "proposed" ? onDecision : undefined
                }
              />
            ))}
          </section>
        ))}
      {(!proposal.context_review.contract ||
        !proposal.context_review.issues?.length) &&
        proposal.context_review.unresolved.map((item) => (
          <p
            key={`${item.unit_ids.join(",")}-${item.reason}`}
            className="text-warning"
          >
            Cần đối chiếu thêm ({item.unit_ids.join(", ")}): {item.reason}
          </p>
        ))}
      {proposal.review?.context_decisions?.map((item) => (
        <p key={item.issue_id}>
          Đã đối chiếu {item.issue_id}: {item.reason} · {item.actor_id}
        </p>
      ))}
      {proposal.review?.machine_validation && (
        <p>
          Quyết định chấp thuận hàng loạt của {proposal.review.actor_id} lúc{" "}
          {proposal.review.at}.{" "}
          {proposal.review.machine_validation.auto_verified_count} mục được hệ
          thống kiểm chứng theo {proposal.review.machine_validation.policy_id} /{" "}
          {proposal.review.machine_validation.policy_version}; không ghi nhận
          người dùng đã đọc riêng từng mục.
        </p>
      )}
    </section>
  );
  if (proposal?.status !== "proposed" || !proposal.annotations) {
    const policy = artifact.source_policy;
    return (
      <>
        {contextPanel}
        {policy ? (
          <p role="status" className="text-sm text-muted-foreground">
            Còn {policy.semantic_unknown_count} ô chưa rõ nghĩa; đã xác nhận{" "}
            {policy.acknowledged_limit_count} giới hạn nguồn; còn{" "}
            {policy.unfinished_count} ô cần xử lý. Xuất bản có giới hạn chưa
            được bật.
          </p>
        ) : null}
      </>
    );
  }
  const sourceTextFor = (id?: string) =>
    artifact.retrieval_units?.units.find((unit) => unit.id === id)?.text;
  return (
    <section
      aria-label="Đề xuất ngữ nghĩa chờ đối chiếu"
      className="space-y-3 text-sm"
    >
      {contextPanel}
      <p className="break-all text-muted-foreground">
        Đề xuất hiện hành: {proposal.proposal_hash ?? "Chưa có hash"} · nguồn:{" "}
        {proposal.input_hash ?? "Chưa có mã kiểm chứng"}
      </p>
      <p className="font-medium">
        Đề xuất ngữ nghĩa cần bạn đối chiếu ({proposal.annotations.notes.length}{" "}
        quan hệ)
      </p>
      <p className="text-muted-foreground">
        Chưa áp dụng vào dữ liệu hoặc câu trả lời. Hãy kiểm tra phạm vi và trích
        đoạn dưới đây trước khi duyệt.
      </p>
      {proposal.context_review && (
        <div className="space-y-2 rounded-lg border p-3">
          <p>
            Phạm vi phân tích:{" "}
            {proposal.context_review.scope === "selected_tables"
              ? "các bảng được chọn"
              : "tài liệu"}
            .{" "}
            {proposal.context_review.coverage_complete
              ? "Đã cấp đủ các gói trong phạm vi này; ngữ nghĩa vẫn cần người duyệt."
              : "Ngữ cảnh chưa đủ; chưa được áp dụng đề xuất."}
          </p>
          {proposal.context_review.unresolved.map((item) => (
            <p
              key={`${item.unit_ids.join(",")}-${item.reason}`}
              className="break-words text-warning"
            >
              Cần đối chiếu thêm ({item.unit_ids.join(", ")}): {item.reason}
            </p>
          ))}
        </div>
      )}
      {proposal.annotations.notes.map((note, noteIndex) => {
        const index = artifact.tables.findIndex(
          (table) => table.id === note.table_id,
        );
        const table = artifact.tables[index];
        return (
          <article
            key={`${note.evidence_binding?.evidence_id ?? note.note_unit_id}-${note.table_id}-${note.scope}-${note.row_unit_ids.join(",")}-${note.column_ids.join(",")}`}
            className="space-y-2 rounded-lg border p-3"
          >
            <p className="font-medium">
              {proposal.context_review?.display_labels?.assertions?.[
                proposal.context_review?.assertion_ids?.[noteIndex] ?? ""
              ] ?? `Quan hệ ${noteIndex + 1}`}{" "}
              · Bảng {index + 1} · {scopeLabels[note.scope]}
            </p>
            {note.context_kind === "workflow" && (
              <div className="space-y-1">
                <p>{note.context_label}</p>
                <p>
                  Ngữ cảnh hồ sơ hoặc quy trình có điều kiện, không trực tiếp
                  sửa dữ liệu số của bảng. Tập dòng xác định chủ thể cần xét,
                  không có nghĩa mọi hồ sơ đều đủ điều kiện.
                </p>
              </div>
            )}
            {table && note.row_unit_ids.length > 0 && (
              <p>
                Dòng:{" "}
                {note.row_unit_ids
                  .map((row) => rowLabel(table, row))
                  .join("; ")}
              </p>
            )}
            {table && note.column_ids.length > 0 && (
              <p>
                Cột:{" "}
                {note.column_ids
                  .map(
                    (id) =>
                      table.columns
                        ?.find((column) => column.id === id)
                        ?.header_path.join(" / ") ?? "Cột không còn tồn tại",
                  )
                  .join("; ")}
              </p>
            )}
            <blockquote className="whitespace-pre-wrap border-l-2 pl-3 text-muted-foreground">
              {note.evidence_quote}
            </blockquote>
            <EvidenceReviewDetails
              binding={note.evidence_binding}
              reason={note.reason}
              sourceText={sourceTextFor(
                note.evidence_binding?.source_unit_id ?? note.note_unit_id,
              )}
            />
            {note.related_evidence?.map((binding) => {
              const sourceText = sourceTextFor(binding.source_unit_id);
              return (
                <details key={binding.evidence_id} className="space-y-2">
                  <summary>Tham chiếu và điều kiện đi kèm</summary>
                  <SourceEvidenceLink binding={binding} />
                  <EvidenceReviewDetails
                    binding={binding}
                    sourceText={sourceText}
                  />
                </details>
              );
            })}
          </article>
        );
      })}
      {proposal.annotations.cells.map((cell) => {
        const table = artifact.tables.find((item) =>
          item.row_unit_ids?.includes(cell.row_unit_id),
        );
        return (
          <article
            key={`${cell.row_unit_id}-${cell.column_id}`}
            className="space-y-2 rounded-lg border p-3"
          >
            <p className="font-medium">
              {table
                ? rowLabel(table, cell.row_unit_id)
                : "Dòng không còn tồn tại"}
            </p>
            <p>
              {table?.columns
                ?.find((column) => column.id === cell.column_id)
                ?.header_path.join(" / ")}
              : “{cell.raw}” → {stateLabels[cell.state]}
            </p>
            <blockquote className="whitespace-pre-wrap border-l-2 pl-3 text-muted-foreground">
              {cell.evidence_quote}
            </blockquote>
            <EvidenceReviewDetails
              binding={cell.evidence_binding}
              reason={cell.reason}
              sourceText={sourceTextFor(
                cell.evidence_binding?.source_unit_id ?? cell.evidence_unit_id,
              )}
            />
          </article>
        );
      })}
      {(proposal.annotations.limitations ?? []).map((item) => {
        const table = artifact.tables.find((value) =>
          value.row_unit_ids?.includes(item.row_unit_id),
        );
        return (
          <article
            key={`limit-${item.row_unit_id}-${item.column_id}`}
            className="space-y-2 rounded-lg border p-3"
          >
            <p className="font-medium">Giới hạn nguồn cần xác nhận riêng</p>
            <p>
              {table ? rowLabel(table, item.row_unit_id) : item.row_unit_id} ·{" "}
              {table?.columns
                ?.find((column) => column.id === item.column_id)
                ?.header_path.join(" / ")}
              : “{item.raw}”
            </p>
            <p>
              {item.basis === "source_explicit"
                ? "Đề xuất: nguồn nói rõ chưa cung cấp nghĩa/giá trị."
                : "Cần bạn kiểm tra toàn bộ phạm vi dưới đây và xác nhận chưa tìm thấy định nghĩa trong phạm vi đó."}
            </p>
            <blockquote className="whitespace-pre-wrap border-l-2 pl-3 text-muted-foreground">
              {item.evidence_quote}
            </blockquote>
            <EvidenceReviewDetails
              binding={item.evidence_binding}
              reason={item.reason}
              sourceText={sourceTextFor(
                item.evidence_binding?.source_unit_id ?? item.evidence_unit_id,
              )}
            />
            <details>
              <summary>
                Đọc phạm vi cần đối chiếu ({item.examined_unit_ids.length} đơn
                vị)
              </summary>
              <div className="space-y-2 break-words">
                {item.examined_unit_ids.map((id) => (
                  <p key={id}>
                    <span className="font-medium">{id}</span>:{" "}
                    {artifact.retrieval_units?.units.find(
                      (unit) => unit.id === id,
                    )?.text ??
                      "Không tải được nội dung; chưa đủ căn cứ xác nhận."}
                  </p>
                ))}
              </div>
            </details>
            <p className="text-muted-foreground">
              Giữ raw và trạng thái dữ liệu. Chỉ mô tả giới hạn; không dùng làm
              số, không quy về 0 hay mượn ô/năm khác. Xác nhận này ghi vào bản
              nháp; xuất bản vẫn bị chặn.
            </p>
          </article>
        );
      })}
    </section>
  );
}

function evidenceAnchor(unitId: string) {
  return `semantic-source-${encodeURIComponent(unitId)}`;
}

function SourceEvidenceLink({ binding }: { binding: SemanticEvidenceBinding }) {
  return (
    <a
      className="text-primary underline break-all"
      href={`#${evidenceAnchor(binding.source_unit_id)}`}
    >
      Nguồn {binding.source_unit_id} · [{binding.start}, {binding.end})
    </a>
  );
}

export function SemanticReviewPreview(
  props: Parameters<typeof SemanticReviewContent>[0],
) {
  const proposal = props.artifact.semantic_annotations;
  const sources = new Map<string, { text: string; references: Set<string> }>();
  if (proposal?.status !== "proposed" && !proposal?.context_review)
    return <SemanticReviewContent {...props} />;
  const register = (
    binding: SemanticEvidenceBinding | null | undefined,
    quote: string,
    reference: string,
  ) => {
    if (!binding?.source_unit_id) return;
    const id = binding.source_unit_id;
    const canonical = props.artifact.retrieval_units?.units.find(
      (unit) => unit.id === id,
    )?.text;
    const previous = sources.get(id);
    const text =
      canonical ??
      (quote.length > (previous?.text.length ?? 0)
        ? quote
        : (previous?.text ?? quote));
    const references = previous?.references ?? new Set<string>();
    references.add(reference);
    sources.set(id, { text, references });
  };
  for (const issue of proposal?.context_review?.issues ?? []) {
    const label =
      proposal?.context_review?.display_labels?.issues?.[issue.issue_id] ??
      issue.issue_id;
    for (const item of issue.review_evidence ?? [])
      register(item.evidence_binding, item.evidence_quote, label);
  }
  for (const assessment of proposal?.context_review?.reference_assessments ??
    []) {
    for (const item of assessment.evidence)
      register(item.evidence_binding, item.evidence_quote, assessment.issue_id);
    for (const link of assessment.links ?? [])
      for (const item of link.evidence)
        register(item.evidence_binding, item.evidence_quote, link.assertion_id);
  }
  for (const note of proposal?.annotations?.notes ?? []) {
    register(note.evidence_binding, note.evidence_quote, note.note_unit_id);
    for (const binding of note.related_evidence ?? []) {
      const text = props.artifact.retrieval_units?.units.find(
        (unit) => unit.id === binding.source_unit_id,
      )?.text;
      register(
        binding,
        text === undefined
          ? "Chưa tải được nội dung tham chiếu; cần bổ sung trước khi duyệt."
          : Array.from(text).slice(binding.start, binding.end).join(""),
        note.note_unit_id,
      );
    }
  }
  for (const cell of proposal?.annotations?.cells ?? [])
    register(cell.evidence_binding, cell.evidence_quote, cell.row_unit_id);
  for (const limit of proposal?.annotations?.limitations ?? [])
    register(limit.evidence_binding, limit.evidence_quote, limit.row_unit_id);
  return (
    <>
      <SemanticReviewContent {...props} />
      {sources.size > 0 && (
        <details className="space-y-2 text-sm">
          <summary className="cursor-pointer font-medium">
            Nguồn đối chiếu dùng chung ({sources.size})
          </summary>
          {Array.from(sources, ([id, source]) => (
            <article
              id={evidenceAnchor(id)}
              key={id}
              className="space-y-2 rounded-lg border p-3"
            >
              <p className="break-all font-medium">{id}</p>
              <p className="break-all text-muted-foreground">
                Liên quan: {Array.from(source.references).join("; ")}
              </p>
              <blockquote className="whitespace-pre-wrap break-words border-l-2 pl-3">
                {source.text}
              </blockquote>
            </article>
          ))}
        </details>
      )}
    </>
  );
}
