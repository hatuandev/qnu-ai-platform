# Phiên 487 — Kiểm tra nhanh ba câu RAG

Ngày 2026-10-16. User yêu cầu thử 3 câu; không yêu cầu sửa code.
Dùng skill qnu-rag-evaluation, đọc pipeline hiện có. Chạy service chat thật mà API
assistant sử dụng, qua `trace_case`, cùng conversation mới cho ba lượt, không qua UI.
Model policy primary qwen3.5-9b / prov_rtx5090_vllm; factory và HTTP transport chặn
provider bên ngoài. Không thay cấu hình, nguồn, vector, publication hoặc kích hoạt glossary.
Chat thử tạo conversation/usage/gap records bình thường; không phải giao dịch read-only toàn bộ.

## Thực chạy

- Harness tái dùng `scripts.probe_conversation_acts_476` với đúng 3 câu thay danh sách
  trong bộ nhớ; không sửa file script hay ứng dụng. Giới hạn 240 giây/lượt có sẵn.
- Lượt đầu sandbox: primary/embedding ConnectError, fallback ngoài bị chặn;
  hai câu lỗi ALL_PROVIDERS_UNAVAILABLE, câu ba insufficient_context.
  Giữ log ở `backend/storage/rag_enumeration_487/smoke3_4287c28b.json`.
- Chẩn đoán kết nối: `/v1/models` nội bộ trả 200 khi chạy ngoài sandbox. Đây là lý do
  chạy lại cùng ba câu với quyền kết nối, conversation mới, không đổi model/reset breaker.
- Lượt có kết nối: `backend/storage/rag_enumeration_487/smoke3_network_79dcad1c.json`;
  hoàn thành 3/3, không lỗi hạ tầng, không có fallback ngoài bị gọi/chặn trong lượt này.
  Không có dữ liệu gửi ra provider ngoài. Các JSON là artifact local, không commit.

## Kết quả quan sát

1. “Trường Đại học Quy Nhơn áp dụng những phương thức xét tuyển nào năm 2026?”
   — answered, 18475.37 ms; nêu PT1–PT5, xét tuyển thẳng và điều kiện ngành sư phạm.
   Có 5 đoạn trích từ 2 nguồn. Nội dung chính khớp đoạn trích đã kiểm tra; chưa chấm
   exhaustively mọi mệnh đề phụ hoặc coi groundedness là correctness toàn bộ.
2. “Bạn giải thích ngắn gọn, dễ hiểu hơn giúp tôi nhé.”
   — insufficient_context, 542.60 ms, ACT_REQUIRES_CLARIFICATION, 0 citation.
   Resolver nhận đúng mode explain và đúng antecedent câu 1. Nhưng conversation_acts
   hiện chỉ hỗ trợ tái dựng danh sách tổ hợp; antecedent không có query_subjects nên
   trả None, service.ask biến thành hỏi làm rõ. Đây là thiếu phạm vi xử lý follow-up,
   không phải mất history hoặc model không hiểu ngữ cảnh.
3. “Ngành Sư phạm Toán học năm 2026 xét tuyển những tổ hợp môn nào?”
   — insufficient_context, 398.92 ms, NO_COMPATIBLE_FACT_EVIDENCE, 0 citation.
   Đọc DB chỉ SELECT: có 4 fact subject_combinations trên active bindings liên quan,
   nhưng cả 4 applicability_year=NULL; guard 2026 không nhận chúng. Không kết luận
   “không có dữ liệu”. Tên file có 2025/2026 không đủ chứng minh năm dữ liệu của dòng.
   Phản hồi còn ghép lời từ chối chung + lời chào/danh sách gợi ý/liên hệ từ cấu hình,
   dài và dễ gây hiểu lầm rằng tài liệu hoàn toàn thiếu thông tin.

## Bằng chứng và giới hạn

- Config/snapshot/target data/collection metadata/inventory fingerprints trước/sau
  trùng theo harness. Đây không phải full DB fingerprint hoặc kiểm chứng mọi corpus byte.
- Một truy vấn diagnostic đầu tiên dùng nhầm `f.temporal_context` bị UndefinedColumn;
  đã sửa truy vấn SELECT thành đọc `raw_data`; không phải lỗi phát sinh từ app/schema.
- Tổng: 1 lượt answered cơ bản phù hợp, 2 lượt chưa đáp ứng; không phải tỷ lệ chất lượng
  đại diện 82 câu. Glossary đang tắt/rỗng nên ba lượt không chứng minh expansion hoạt động.
- Không sửa code, không test suite/build, không reindex/restart/push trong phiên này.

## Hướng xử lý đề xuất, chưa triển khai

- Cho explain/reformat câu trả lời thông thường dùng lại evidence đã xác minh của
  lượt trước; kiểm tra snapshot/quyền/phạm vi và không thêm dữ kiện mới.
- Xác minh năm áp dụng từ bằng chứng nội dung/header của nguồn và gắn ở cấp dòng;
  không tự gán năm từ filename. Khi chưa rõ, giải thích “có tổ hợp nhưng chưa xác minh
  năm 2026”, thay vì khẳng định dữ liệu không có.
- Bỏ lời từ chối/lời chào lặp, làm rõ missing scope khác thiếu dữ liệu.
