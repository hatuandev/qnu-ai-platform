# Phiên 1010 — Nhiều kho tri thức cho trợ lý (P1–P5)

## Thay đổi

- **Hợp đồng**: `AssistantCreate/Update.collection_ids` (tối đa 20, khử trùng)
  và `AssistantResponse.collection_ids`; cột vô hướng `collection_id` vẫn phản
  chiếu phần tử đầu để tương thích. Snapshot hội thoại mang `collection_ids`.
  Cập nhật từ client cũ không gửi `collection_ids` bị thu về đúng kho vô hướng
  theo hợp đồng, nên form V2 luôn gửi lại đủ bộ.
- **Truy xuất**: `knowledge/index/multi.py` fan-out từng kho đã cấp quyền, gộp
  theo RRF (`fusion: "rrf_collections"`), rerank một lần toàn cục; trace ghi
  trạng thái/số trúng/generation từng kho. Câu hỏi nhiều vế tách facet như cũ.
- **Chặng dùng bộ kho hiệu lực**: hội thoại, kiểm thử câu trả lời, kênh công
  khai, gateway và lịch sử đều đọc `collection_ids` từ snapshot/revision.
- **Giao diện**: tab Cấu hình chọn nhiều kho kèm cảnh báo; tab Tổng quan hiện
  "N kho" và từng dòng sẵn sàng theo kho khi có hơn một kho.
- **Sửa nhỏ từ kiểm chứng P5**: bảng mã lỗi lượt hỏi thêm
  `answer_scope_clarification_required` để nhật ký giải thích việc cần nêu rõ
  phạm vi ngành/khóa/năm thay vì chỉ báo "Lượt hỏi thất bại".

## Kiểm chứng

- Dev stack :8002/:3002, workspace `ws_623614ba7fb8`, trợ lý
  `ast_44fc63a77512` revision 7 gắn 2 kho: "Tuyển sinh đại học QNU 2025"
  (`cdoc_435003928b2a`) và "Tuyển sinh QNU 2026 · Văn bản thuyết minh"
  (`cdoc_57b443f613e9`).
- Hội thoại `cnv_3e90af439f10`, 7 lượt: lượt 5 (học phí) và lượt 7 (chính sách
  sư phạm) trả lời trong 12 giây, cả hai kho đều `served` 40 trúng, rerank toàn
  cục; lượt 5 dẫn `cdoc_435003928b2a`, lượt 7 dẫn `cdoc_57b443f613e9` — trích
  dẫn đến từ cả hai tài liệu. Lượt 1–4 và 6 trả 409
  `answer_scope_clarification_required`: câu không nêu phạm vi hoặc nêu năm
  2026 vốn vừa là năm dữ liệu vừa là năm ban hành trong danh mục hai kho, cổng
  làm rõ từ chối tự chọn năm (thiết kế giữ nguyên, không nới).
- Kiểm thử câu trả lời `arv_2127f71b3693` (revision 7, 2 câu): cả hai đạt
  `answered`, mỗi câu dẫn đúng một tài liệu và cả hai kho `served`; gửi lại
  cùng Idempotency-Key trả 200 cùng id; dùng key đó với nội dung khác trả 409
  `idempotency_conflict`.
- Nhật ký trên giao diện hiển thị đủ 7 lượt kèm câu trả lời/nguồn/số token của
  lượt đạt; lượt lỗi hiện đúng lý do phạm vi sau khi thêm mã lỗi.
- Biome và `tsc --noEmit` đạt trên tệp Frontend vừa sửa. Không đổi backend
  trong phiên này.
- Kênh công khai đang tắt ("Đang tắt") nên kiểm thử kênh công khai cho trợ lý
  hai kho **NOT RUN**. Full suite backend, reindex, migration và trình duyệt
  khác **NOT RUN**; chưa commit/push.
