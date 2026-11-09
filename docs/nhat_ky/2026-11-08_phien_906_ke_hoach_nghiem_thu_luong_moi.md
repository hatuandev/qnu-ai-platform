# Phiên 906 — Kế hoạch hoàn thiện và nghiệm thu luồng mới

- Ngày: 2026-11-08. Phạm vi: lập kế hoạch theo yêu cầu người dùng; không triển khai runtime trong phiên.
- Baseline đọc: `f3f47284`, nhánh `feat/v1-user-workflow`; giữ nguyên thay đổi đồng thời ở backend, KH15, runbook và Context905.

## Yêu cầu và phương pháp

Người dùng cần kế hoạch chi tiết để hoàn thành và đánh giá luồng KH15 bằng model đã seed, đặc biệt Chat phải dùng Qwen qua llama.cpp. Đọc KH15, runbook46, preparation/compiler, ModelOps, schema evaluation, runner admissions và quy định kiểm chứng.

Truy vấn DB local trong transaction `READ ONLY`, chỉ chọn defaults/provider và trường cấu hình an toàn, không đọc/xuất credential. Xác nhận mặc định hệ thống và workspace SHL: `qwen3.8-27b-q4`, `bge-m3`, `bge-reranker-v2-m3`, `mineru`; có `cx/gpt-6-luna` nhưng không dùng thay Qwen cho kế hoạch này. Chính sách Qwen đã lưu tắt reasoning cho bốn task và `wait_for_completion=true`; metadata context/output 163840/32768 được ghi ngày05/11, không xác nhận build/giới hạn slot hiện tại hoặc reasoning đã tắt thực tế.

Đọc manifest 8 tài liệu local bằng SHA256, thống kê PDF text/page và DOCX XML (không gọi parser/model live). D01 4 bảng/1 section, D02 10 bảng/5 section; các PDF tương ứng 14/32/8/13/7/18 trang, riêng Quy chế363 không có text ở 32 trang. Kiểm tra này không thay đối chiếu ngữ nghĩa/parser/OCR.

## Thay đổi tài liệu

- Thêm [KH16](../ke_hoach/16_hoan_thien_va_nghiem_thu_luong_chuan_bi_noi_dung.md): G0–G6, policy tự động, canonical + AI riêng, màn kết quả/gửi duyệt, model preflight, 8 nguồn, 97 câu/biến thể, A/B 194 record, ma trận độ bền và tiêu chí chất lượng/tốc độ/pilot.
- Nêu gap runner hiện có: nhãn 53 câu còn draft, `semantic_review` NOT_RUN; phép so byte trực tiếp với token cần regression trước tái dùng; Sheet 3 câu không đủ thay benchmark.
- Cập nhật mục lục kế hoạch, nhật ký, WORK_LOG, PROJECT_CONTEXT và snapshot906; không đổi kế hoạch15/runbook đang được công việc khác chỉnh.

## Kiểm chứng

- Git/status/log và đọc mã: thực chạy, không mutation runtime.
- Truy vấn ModelOps read-only: exit0, xác nhận cấu hình nêu trên; không có live probe.
- Kiểm manifest: lượt đầu lỗi encoding stdout Windows (UnicodeEncodeError); chuyển stdout UTF-8 và `pymupdf`, lượt kiểm kê 8 file hoàn tất exit0. Đây là kiểm kê file, không phải retry câu hỏi/model.
- Kiểm liên kết local, UTF-8 không BOM/LF, code fences và mục bắt buộc trên 3 tài liệu mới: PASS, exit0; KH16 254 dòng. `git diff --check` trên 4 mục lục/memory sửa: PASS, exit0; diff chỉ thêm các mốc cần thiết và sửa trạng thái KH15 cũ trong mục lục.
- Unit/integration/build/live Qwen/MinerU/RAG A/B/pilot cho KH16: **NOT RUN** — phiên này lập kế hoạch.

Không restart, migrate, seed lại, clear/reset, upload, gọi model, publish/reindex, commit/push hoặc deploy. Bước đầu khi triển khai là G0 xác minh hợp đồng Qwen llama.cpp và đóng baseline thử độc lập; chưa thể kết luận luồng mới đạt chất lượng thực tế.
