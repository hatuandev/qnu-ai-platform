# Phiên 437 — Triển khai kiểm chứng completeness cho RAG/DAG

Ngày 2026-10-14. Người dùng xác nhận triển khai phương án trong báo cáo kiểm thử 20 câu sau khi xuất bản văn bản thuyết minh tuyển sinh 2026.

## Mục tiêu

- Ngăn verifier cho qua một claim có vế quan hệ không được nguồn chứng minh.
- Tách trường đích của câu hỏi khỏi đơn vị tổ chức kỳ thi.
- Giữ dữ liệu lịch sử theo đúng vai trò năm dữ liệu, đồng thời tránh nhóm liệt kê sai chủ đề chiếm context.
- Bảo toàn câu trả lời partial đã có chứng cứ khi một lượt sửa quote bị thất bại.

## Thay đổi chính

- Thêm `evidence_audit.py`: semantic audit theo claim nguyên tử, kiểm tra span claim, quote chứng minh, qualifiers bắt buộc và coverage; không cho tự cộng các thông báo liên tiếp nếu người dùng không hỏi tổng lũy kế.
- Thêm `evidence_scope.py`: resolve `target_institution`/`exam_organizer` bằng hợp đồng riêng; tên đơn vị tổ chức SPT không còn tự thay thế trường đích QNU.
- Thêm `evidence_verification.py`: dùng chung cho RAG và DAG, kiểm chứng temporal/scope, audit completeness và retry có giới hạn khi verifier gán `superseded_by` không có proof cùng tuple.
- Thêm projection context compact với `source_context` của cùng source revision; source context chỉ giải quyết chủ thể/pronoun, không trở thành quote hay năm dữ liệu mới.
- Cập nhật selection/packing: giữ direct attribute hits, mở rộng list theo subject, ưu tiên data-year trong BM25, gắn heading/parent cùng nguồn và ghi diagnostics `packed_characters`, `dropped`.
- Khi semantic repair không đưa ra claim hợp lệ, giữ lại các claim partial đã kiểm chứng trước đó thay vì biến toàn bộ câu trả lời thành no-answer.

## Tệp chính

- `backend/app/modules/rag/evidence_audit.py`
- `backend/app/modules/rag/evidence_context.py`
- `backend/app/modules/rag/evidence_scope.py`
- `backend/app/modules/rag/evidence_verification.py`
- `backend/app/modules/rag/evidence_blocks.py`
- `backend/app/modules/rag/evidence_bm25.py`
- `backend/app/modules/rag/evidence_model.py`
- `backend/app/modules/rag/evidence_pipeline.py`
- `backend/app/modules/rag/evidence_schemas.py`
- `backend/tests/test_evidence_completeness_437.py`

## Kiểm thử

- `uv run ruff check` trên các module và test liên quan: đạt.
- Bộ hồi quy RAG/DAG/evidence/temporal: **95 passed**.
- Kiểm tra thực tế câu 13 sau sửa: RAG trả `partial` với claim QNU dùng PT4 và giữ rõ phần ngành/tổ hợp cần công bố; không còn nhầm ĐHSP Hà Nội là trường đích. Phần chưa có danh sách ngành cụ thể vẫn được đánh dấu thiếu. Lượt DAG cùng đợt chạy trên tiến trình BE chưa reload đầy đủ source mới, nên cần restart BE/worker trước khi dùng kết quả live làm nghiệm thu.
- Kiểm tra thực tế câu 16: trả lời giữ điều kiện “nếu ngành cho phép”, không khẳng định gộp điểm hay ép phương thức; phần ngưỡng/bảng riêng chỉ được nêu khi nguồn trực tiếp chứng minh.
- Lượt kiểm tra 13/16 có HTTP 200 nhưng thời gian 21–51 giây; đây là độ trễ nhiều bước ModelOps, chưa phải cơ sở tăng `max_tokens` UI 5000.
- Full backend suite: **1208 passed, 11 failed, 15 skipped** trong 168,05 giây. 11 lỗi thuộc các nhóm baseline consulting export/universal tools, publishing v2/GC/canary, reconciliation và auth session cookie; không phát sinh ở nhóm RAG/evidence vừa sửa và không được sửa trong phiên này.

## Giới hạn và bước tiếp theo

Chưa chạy lại đủ 82 câu, chưa Ragas, chưa reindex/publish/reset DB và không đổi model/provider. Trước khi test live, cần restart backend/worker để nạp module mới. Sau đó chạy lại nhóm 20 hồi quy, rồi mới cân nhắc toàn bộ 82; các câu thật sự thiếu nguồn phải giữ no-answer/partial có trích dẫn.

