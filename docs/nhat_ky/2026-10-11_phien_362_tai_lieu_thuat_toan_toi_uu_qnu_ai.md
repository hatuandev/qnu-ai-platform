# Phiên #362 — Tài liệu thuật toán nâng chất lượng và tối ưu

## Mục tiêu và phạm vi

Theo yêu cầu người dùng, tạo file Markdown tổng hợp thuật toán/kỹ thuật có thể áp dụng cho repo. Không triển khai runtime, sửa qnu-sso, cấu hình provider hoặc tác động dữ liệu/dịch vụ.

## Nội dung

Tạo `docs/ke_hoach/13_thuat_toan_nang_cao_chat_luong_va_toi_uu_qnu_ai.md`: hiện trạng so đề xuất; BM25/RRF/reranker, parent-child, dedup/MMR, multi-query, pg_trgm, learned sparse, ColBERT/HyDE; HNSW/quantization/cache/OCR-worker và DAG. Phân biệt DAG với GraphRAG, scope/lifecycle với thuật toán, model capability với API server capability. Đưa lộ trình có gate, benchmark thật và không ép triển khai tất cả.

Skills RAG và clean-code giúp giữ một pipeline chung, tối ưu thành phần đã có và lựa chọn theo bằng chứng. Đối chiếu nguồn chính thức PostgreSQL/Qdrant/FlagEmbedding và nghiên cứu được dẫn cạnh các mục liên quan. Hiện trạng dựa trên #361 và đọc code trọng tâm; không suy ra toàn hệ đã production-ready.

## Tệp thay đổi

Tài liệu 13 và index kế hoạch; nhật ký/index; PROJECT_CONTEXT, snapshot #362 và WORK_LOG. Không sửa tài liệu quy trình runtime vì chưa thay đổi luồng đang chạy.

## Kiểm chứng

Kiểm tra whitespace diff, UTF-8 nghiêm ngặt và các link local trong tài liệu mới. Không chạy Ruff/Pytest/build/E2E vì chỉ sửa Markdown. Kết quả 25 tests ở #361 là bằng chứng phiên trước, không tính là test mới hoặc benchmark các thuật toán đề xuất.

## Bàn giao

File là hướng dẫn lựa chọn và ưu tiên, không phải lệnh tự động triển khai/reset. Người dùng chọn phạm vi đợt tiếp theo trước khi đổi code hoặc hạ tầng.
