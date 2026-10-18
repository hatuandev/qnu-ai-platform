import type { SourceArtifact } from "@/types/knowledge";

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

export function SemanticReviewPreview({
  artifact,
}: {
  artifact: SourceArtifact;
}) {
  const proposal = artifact.semantic_annotations;
  if (proposal?.status !== "proposed" || !proposal.annotations) return null;
  const rowLabel = (table: SourceArtifact["tables"][number], row: string) => {
    const index = table.row_unit_ids?.indexOf(row) ?? -1;
    return index < 0
      ? "Dòng không còn tồn tại"
      : table.rows[index]?.slice(0, 3).filter(Boolean).join(" · ");
  };
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
          </article>
        );
      })}
    </section>
  );
}
