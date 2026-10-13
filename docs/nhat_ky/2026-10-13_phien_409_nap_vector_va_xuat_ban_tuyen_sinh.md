# Phiên #409 — Nạp vector và xuất bản kho tuyển sinh

## Yêu cầu và thực thi

Người dùng đã duyệt toàn bộ tài liệu và yêu cầu nạp vector, xuất bản `col_admissions`, đồng thời sửa vấn đề phát hiện trong quá trình vận hành.

- API xác nhận 19 binding active, source ready và `requires_structured_review=false`; sau reset của người dùng không còn vector generation.
- Đọc model/provider/dimension từ cấu hình ModelOps hiện tại: `bge-m3`, `prov_rtx5090_vllm`, 1024 chiều. Không sửa cấu hình provider hay model mặc định.
- Tạo generation `vg_75acf82ded93` lúc 10:04 ngày 13/10/2026 (UTC+7), queue đúng 19 source revisions đang active qua API `vector-load`.
- Worker hoàn thành 19/19 job, không job failed/cancelled. PostgreSQL có 19 index ready, 227 chunks và 3428 facts; cả 19 parity report đều đạt.
- API activate xuất bản thành công generation trên, epoch 2; 19 binding có active index pointer và generation active.
- Qdrant collection `col_admissions_169f2ef17edd4ae5` có đúng 227 points được bật `is_retrievable=true` cho generation mới.
- Hai truy xuất RAG thật: phương thức tuyển sinh 2026 (5 kết quả, 450.69ms) và học phí K49 (5 kết quả, 435.09ms). Snapshot epoch2 pin đủ 19 bindings/generation; học phí K49 đứng đầu với đúng văn bản và trang.

## Vấn đề phát hiện và bản sửa

API summary sau xuất bản trả `total_sources=0` và `configured_embedding_model=null`, trong khi đã xuất bản 19 tài liệu. Summary đếm `KnowledgeGroupSource` (liên kết nhóm) thay vì `KnowledgeBinding` (nguồn tài liệu trực tiếp/snapshot), và chỉ đọc cấu hình chưa xuất bản trong `data_processing`.

- Đếm bindings giống bộ lọc danh sách nguồn: collection/tenant/workspace, loại detached/deleting.
- Vẫn giữ group links phục vụ trạng thái và đối soát đồng bộ; collection có nhóm chưa materialize không bị coi là empty.
- Đọc embedding đang phục vụ từ metadata active generation, rồi mới fallback cấu hình data_processing.
- API runtime sau reload đã trả đúng 19 nguồn / 19 published / 227 active chunks / ready / bge-m3.

## Tệp thay đổi

- `backend/app/modules/knowledge/services/group_source_service.py`
- `backend/tests/test_collection_summary_metrics.py`

## Kiểm tra

- Regression ban đầu tái hiện đúng `total_sources=0`, trạng thái empty sai và model cấu hình cũ.
- Summary và group source suites: `35 passed, 1 skipped`, có ca DB unavailable phải lộ lỗi, không dùng fallback empty.
- Ruff toàn backend: đạt (cảnh báo quyền thư mục temp cũ).
- Full backend: `990 passed, 11 failed, 9 errors, 3 skipped`; các failure/error cùng baseline ngoài phạm vi từ phiên407 (Windows temp, RBAC/role test cũ, exporter/consulting/reconciliation). Ba regression mới đều đạt.
- Không sửa frontend nên không chạy Vite build lại; build frontend gần nhất ở phiên408 đã đạt.

## Giới hạn và quyết định

Đã xác minh index/publication/retrieval thật; chưa đánh giá đầy đủ chất lượng mọi câu trả lời LLM hoặc Ragas. Không OCR/bóc tách lại, không reset DB/Redis, không tự thay kết quả duyệt hoặc chỉnh số liệu người dùng đã đối soát. Các bước runtime giữ snapshot/revision isolation và publish gates của RAG/backend skills.
