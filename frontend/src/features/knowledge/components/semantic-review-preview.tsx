import type {
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
          <p className="whitespace-pre-wrap break-words">
            {sourceText ??
              "Không tải được đơn vị nguồn; chưa đủ căn cứ đối chiếu."}
          </p>
        </details>
      )}
    </div>
  );
}

export function SemanticReviewPreview({
  artifact,
}: {
  artifact: SourceArtifact;
}) {
  const proposal = artifact.semantic_annotations;
  if (proposal?.status !== "proposed" || !proposal.annotations) {
    const policy = artifact.source_policy;
    return policy ? (
      <p role="status" className="text-sm text-muted-foreground">
        Còn {policy.semantic_unknown_count} ô chưa rõ nghĩa; đã xác nhận{" "}
        {policy.acknowledged_limit_count} giới hạn nguồn; còn{" "}
        {policy.unfinished_count} ô cần xử lý. Xuất bản có giới hạn chưa được
        bật.
      </p>
    ) : null;
  }
  const rowLabel = (table: SourceArtifact["tables"][number], row: string) => {
    const index = table.row_unit_ids?.indexOf(row) ?? -1;
    return index < 0
      ? "Dòng không còn tồn tại"
      : table.rows[index]?.slice(0, 3).filter(Boolean).join(" · ");
  };
  const sourceTextFor = (id?: string) =>
    artifact.retrieval_units?.units.find((unit) => unit.id === id)?.text;
  return (
    <section
      aria-label="Đề xuất ngữ nghĩa chờ đối chiếu"
      className="space-y-3 text-sm"
    >
      <p className="font-medium">Đề xuất từ model cần bạn đối chiếu</p>
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
      {proposal.annotations.notes.map((note) => {
        const index = artifact.tables.findIndex(
          (table) => table.id === note.table_id,
        );
        const table = artifact.tables[index];
        return (
          <article
            key={`${note.note_unit_id}-${note.table_id}-${note.scope}-${note.row_unit_ids.join(",")}-${note.column_ids.join(",")}`}
            className="space-y-2 rounded-lg border p-3"
          >
            <p className="font-medium">
              Bảng {index + 1} · {scopeLabels[note.scope]}
            </p>
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
