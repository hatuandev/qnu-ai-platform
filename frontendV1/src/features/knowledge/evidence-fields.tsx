const LABELS: Record<string, string> = {
  page_notes: "Chú thích trang",
  text: "Nội dung",
  workspace_id: "Đơn vị",
  collection_id: "Bộ sưu tập",
  data_year: "Năm dữ liệu",
  issued_year: "Năm ban hành",
  valid_from: "Hiệu lực từ",
  valid_to: "Hiệu lực đến",
  program: "Chương trình",
  major: "Ngành",
  role: "Vai trò",
  value: "Giá trị",
  evidence: "Căn cứ",
  citation: "Trích dẫn",
  source_id: "Tài liệu nguồn",
  revision_id: "Phiên bản gốc",
  filename: "Tên tệp",
  page_number: "Trang",
  path: "Vị trí",
  text_version: "Bản sửa hậu OCR",
  canonical_sha256: "Hash nội dung",
  manifest_sha256: "Hash bản kê",
  retrieval_metadata: "Metadata đã khai báo",
  context: "Ngữ cảnh",
  title: "Tiêu đề",
  heading: "Mục",
  parent: "Phần cha",
  position: "Vị trí",
  part: "Phần",
  reason: "Lý do",
  document_id: "Tài liệu",
  chunk_id: "Đoạn",
  score: "Điểm xếp hạng",
  ranking: "Các lượt xếp hạng",
  dense: "Vector",
  lexical: "Từ khóa",
  fusion: "Hợp nhất",
  rerank: "Xếp hạng lại",
  score_kinds: "Thang điểm",
  mode: "Chế độ",
  status: "Trạng thái",
};
export function EvidenceFields({
  value,
  depth = 0,
}: {
  value: unknown;
  depth?: number;
}) {
  if (value === null || value === undefined)
    return <span className="text-muted-foreground">Chưa xác định</span>;
  if (typeof value !== "object")
    return (
      <span className="whitespace-pre-wrap break-words">
        {typeof value === "boolean" ? (value ? "Có" : "Không") : String(value)}
      </span>
    );
  if (depth >= 6)
    return (
      <span className="text-muted-foreground">
        Cấu trúc lồng sâu; xem bản xuất JSON để đối chiếu đầy đủ.
      </span>
    );
  const entries = Object.entries(value);
  if (entries.length === 0)
    return <span className="text-muted-foreground">Chưa có thông tin</span>;
  return (
    <dl className="space-y-2 border-l pl-3">
      {entries.map(([key, child]) => (
        <div key={key} className="min-w-0">
          <dt className="text-xs text-muted-foreground">
            {LABELS[key] ??
              (Array.isArray(value) ? `Mục ${Number(key) + 1}` : key)}
          </dt>
          <dd className="text-sm min-w-0">
            <EvidenceFields value={child} depth={depth + 1} />
          </dd>
        </div>
      ))}
    </dl>
  );
}
