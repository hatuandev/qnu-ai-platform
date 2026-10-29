# Context704 — Nghiên cứu AnythingLLM cho QNU

Ngày: 2026-10-29. Người dùng muốn tìm phần có thể học và áp dụng vào QNU.

## Phạm vi và phương pháp

Nghiên cứu mã công khai AnythingLLM tại commit `0941fb03596862899f7df2bdeb022eb68d4216a7` qua GitHub API/raw,
đọc README bằng web. Tree đệ quy không truncated;36tệp tải thành công có URL/hash trong
artifact local,1đường dẫn embed dự đoán404 đã thay bằng path index đúng. Không chạy mã upstream.
Đối chiếu source backendV1/frontendV1 và giữ các sửa đổi chưa commit của phiên khác.
Dùng skill qnu-clean-code-architect và qnu-frontend-architect cho ranh giới/UX.

## Kết quả

[Báo cáo nghiên cứu](../bao_cao/context704/ANYTHINGLLM_RESEARCH.md):9hướng, ưu tiên
menu theo quyền, folder/upload theo lô, onboarding; tiếp theo citation và tiến trình chat.
Connector/widget/routing nâng cao/tools là giai đoạn sau. Không dựng lại RAG/ModelOps.
Các khác biệt quan trọng: AnythingLLM manager có đường đọc mọi workspace;
combineLikeSources gộp title; QNU giữ membership+role và revision/hash. Conversation QNU
vẫn kiểm owner kể cả platform admin; RAG answer chỉ final sau kiểm nguồn/cấu hình.
Không có kết luận benchmark hay kiểm toán bảo mật tổng thể từ đọc source.

## Kiểm chứng thực chạy

- Git status/diff thực tế đã đọc; source QNU không sửa bởi task này.
- Manifest/revision/tree:36nguồn đã lưu local, không stage mã upstream.
- Kiểm source link/anchor của báo cáo: PASS, 20tham chiếu ghim commit.
- UTF-8 không BOM/LF/không replacement character: PASS.
- Có sửa đồng thời ở knowledge-detail-page và stage-ocr-panel sau snapshot hash;
  không ghi đè, không suy toàn cây nguyên trạng; báo cáo nêu rõ giới hạn snapshot.
- Test/build/benchmark/browser/runtime: NOT RUN vì chỉ nghiên cứu/docs.
- Không DB/config/model/network corpus/reindex/publish/restart/deploy/commit/push.

## Tệp bàn giao

Báo cáo, nhật ký này, snapshot704 và3index memory/work log; artifact tham khảo ở
`storage/artifacts/anythingllm-research/` bị Git bỏ qua. Chưa triển khai các đề xuất.
