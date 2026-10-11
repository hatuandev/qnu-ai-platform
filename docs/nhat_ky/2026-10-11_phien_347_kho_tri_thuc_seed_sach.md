# Phiên #347 — Kho tri thức khởi tạo sạch

## Mục tiêu và nguyên nhân

Người dùng reset DB nhưng tab Dữ liệu số còn 9 facts Tuyển sinh, tab Nguồn tài liệu trống. Seed cũ tạo KnowledgeDocument/chunks/facts legacy; danh sách nguồn dùng KnowledgeBinding ADR-012 nên không thấy tài liệu mẫu. Readiness còn bắt buộc có chunks trong 5 kho, có thể tự seed mẫu lại ở mỗi lần chạy.

## Thay đổi

- `backend/app/modules/knowledge/seeder.py`: default seed chỉ thêm kho trống chưa tồn tại; không overwrite tên/metadata/nội dung có sẵn. Tách hàm nạp nội dung mẫu legacy thành `seed_demo_knowledge`, không nối vào startup/CLI thường.
- `backend/app/cli.py`: core seed verification chỉ yêu cầu providers và default collections đúng scope; bỏ điều kiện phải có chunks.
- `backend/scripts/clear_seed_knowledge.py`: mặc định xem trước; --apply chỉ dọn đúng 5 tài liệu seed gốc nếu checksum, nội dung chunks và giá trị facts còn khớp, không có Repository/index ownership. Có backup toàn bộ hàng DB/metadata trước khi thay đổi, xóa vectors theo document_id trong namespace legacy, không drop collection/generation, tăng index_epoch và invalidate cache. Không xóa storage files/ModelOps.
- `backend/tests/test_clean_knowledge_seed.py`: regression seed không gọi sample helpers; readiness chấp nhận kho trống; preserve settings; DB lỗi không fallback; cleanup từ chối nội dung/file/fact/chunk sửa hoặc ownership Repository/index.
- Đồng bộ Quy trình 01/02, memory, snapshot và các bảng nhật ký.

## Dọn DB thực tế

Preview xác minh đúng 5 bản mẫu: doc_nd30_van_thu, doc_qnu_quy_che_tin_chi, doc_qnu_tuyen_sinh_2024, doc_qnu_cam_nang_thu_vien, doc_qnu_quy_dinh_ngan_hang_cau_hoi. Tổng 32 chunks, 37 facts (Tuyển sinh 9).

Đã chạy --apply: xóa 5 hàng document mẫu cùng chunks/facts cascade, dọn vectors legacy theo từng document khi namespace tồn tại. Giữ 5 kho và mọi cấu hình model/provider, không sửa qnu-sso hay RAG/DAG runtime. Backup storage key:

`maintenance/knowledge-seed-backups/9a89ab6b3524415e9ca59aeff876a198.json`

Readback xác nhận backup có 5 documents và **cả 5 tệp storage mẫu gốc vẫn tồn tại**. Có thể phục hồi hàng DB từ backup; vector cần build lại nếu phục hồi. Không xóa tệp Kho tài liệu của người dùng.

Sau dọn: knowledge_documents=0, knowledge_chunks=0, knowledge_facts=0, knowledge_bindings=0. Chạy lại default seed thật tạo 0 kho/0 docs/0 chunks/0 facts; readiness thật trả True với 11 provider và 5 kho. Không chạy reset DB/migration/restart server.

## Kiểm thử

- 2 regressions chạy fail đúng bug trước sửa (sample helper bị gọi và readiness từ chối kho không có chunks).
- 10 tests mới đạt; cùng test_knowledge cuối phiên **46 passed**.
- Ruff toàn backend đạt, có cảnh báo permission thư mục cũ. uv đôi lúc không đọc được cache; dùng Python/Ruff đã cài trong .venv để hoàn tất kiểm tra.
- Full suite **815 passed / 13 failed / 2 skipped**. 8 failures cũ #346 (6 publishing/GC/canary/direct-upload RBAC fixtures; reconciliation legacy; auth role). 5 failures khác lộ ra khi DB không còn mẫu: consulting dispatcher admissions/regulations exports, fact lookup tool found trong test_tools/test_universal_tools, dynamic admissions export. Những tests này đang phụ thuộc facts seed trong DB runtime thay vì fixture độc lập. Không nạp lại mẫu để làm tests xanh, không thay đổi RAG/tools ngoài phạm vi. Chưa nghiệm thu full suite.
- Không sửa frontend nên không chạy build FE; chưa browser E2E. DB real readback/reseed là bằng chứng khởi tạo sạch.

## Bài học / còn lại

Theo skill backend/clean-code, tách cấu hình bootstrap khỏi nội dung nghiệp vụ và kiểm chứng trước/sau có phạm vi. Cần chuyển 5 tests phụ thuộc live seed sang fixture DB độc lập ở một phiên riêng. Tab Nạp Excel legacy cũng có thể tạo facts không xuất hiện trong danh sách Binding; đó là vấn đề contract khác, chưa sửa trong phiên này.
