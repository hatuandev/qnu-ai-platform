const LABELS: Record<string, string> = {
  resource_status: "Trạng thái hiện tại",
  originals_and_raw_evidence: "Bản gốc và bằng chứng OCR",
  related_history: "Lịch sử liên quan",
  deleted_data: "Dữ liệu sẽ dọn",
  jobs_to_cancel: "Tác vụ sẽ bị hủy",
  published_versions_affected: "Bản xuất bản bị ảnh hưởng",
  assistants_affected: "Trợ lý bị ảnh hưởng",
  conversations_affected: "Hội thoại bị ảnh hưởng",
  revision_count: "Phiên bản nguồn",
  source_count: "Văn bản nguồn",
  restore_requires_new_index: "Cần tạo lại chỉ mục sau khôi phục",
  retires_active_index: "Ngừng chỉ mục đang hoạt động",
  publication_resumes_if_still_current:
    "Có thể phục vụ lại nếu nguồn còn phù hợp",
  cancelled_jobs_restart_automatically: "Tự chạy lại tác vụ đã hủy",
  preserves_originals: "Giữ bản gốc",
  preserves_history: "Giữ lịch sử",
  keeps_current_until_ready: "Giữ bản cũ đến khi bản mới sẵn sàng",
  documents_in_new_index: "Tài liệu trong chỉ mục mới",
  version_id: "Mã phiên bản thay thế",
};
export function ImpactView({ impact }: { impact: Record<string, unknown> }) {
  return (
    <dl className="grid gap-2 text-sm">
      {Object.entries(impact).map(([key, value]) => {
        if (value && typeof value === "object" && !Array.isArray(value))
          return (
            <div key={key} className="space-y-2 border-t pt-2">
              <dt className="font-medium">
                {key === "replacement" ? "Bản thay thế" : key}
              </dt>
              <dd>
                <ImpactView impact={value as Record<string, unknown>} />
              </dd>
            </div>
          );
        const text =
          value === "retained"
            ? "Được giữ nguyên"
            : value === "active"
              ? "Đang hoạt động"
              : value === "archived"
                ? "Đã lưu trữ"
                : value === "deleted"
                  ? "Trong thùng rác"
                  : String(value);
        return (
          <div
            key={key}
            className="flex flex-wrap justify-between gap-2 border-b border-border/50 pb-1"
          >
            <dt className="text-muted-foreground">{LABELS[key] ?? key}</dt>
            <dd className="max-w-full break-all font-medium">
              {typeof value === "boolean"
                ? value
                  ? "Có"
                  : "Không"
                : value === null
                  ? "Chưa xác định"
                  : Array.isArray(value)
                    ? value
                        .map((item) =>
                          item === "inactive_vector_collection"
                            ? "Kho vector đã ngừng dùng"
                            : item === "index_chunks"
                              ? "Các đoạn trong chỉ mục"
                              : String(item),
                        )
                        .join("; ")
                    : text}
            </dd>
          </div>
        );
      })}
    </dl>
  );
}
