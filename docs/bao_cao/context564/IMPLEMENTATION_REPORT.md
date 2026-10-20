# Context564 — Phạm vi thay đổi

| File | Thay đổi |
|---|---|
| `backend/app/modules/rag/evidence_dependencies.py` | `_fact_groups` giữ canonical source row và duyệt refs của nó; `_canonical_context` đóng directed refs bắc cầu; `dependency_groups` dùng closure đó cho explicit canonical refs |
| `backend/app/modules/rag/evidence_blocks.py` | `_complete_packing_group` hoàn tất required refs của thành viên bổ sung; tách required groups khỏi enumeration membership để tránh mở rộng shared note sai; tính budget sau closure |
| `backend/tests/test_evidence_closure_564.py` | 27 test instances cho source row, provenance, pack→projection, directed shared refs, cycles, budget và published fixture |

Không đổi API DTO, database schema, Intent Router, conversation memory, query rewriting, provider selection, model prompts, reranker, chunking hoặc ingestion/semantic annotation. Không reparse/reindex/republish nguồn.

## Tương thích

Caller vẫn dùng `dependency_groups` / `pack_context` và kiểu dữ liệu cũ. Giữ cơ chế rejection và trace `dropped` có sẵn. Payload có thể thêm bằng chứng bắt buộc và một số nhóm có thể bị loại do ngân sách thực của nhóm tăng; không giảm chất lượng để giữ số lượng candidate cũ.

Stable ordering và dedup được kiểm bằng input đảo thứ tự và nhiều facts dùng chung một source row. Bản nguồn, unit identities và hashes giữ nguyên.

## Phạm vi kết quả

Những path dùng packer được sửa; fact/table routing đang chạy vẫn có khoảng hở nhận diện mã và lựa chọn metric, được báo riêng. Không tự bật `evidence_policy.enabled` đang false trong cấu hình trợ lý. Không biến việc sửa closure thành thay cấu hình hoặc đường route để đạt E2E.

Live trace chỉ dùng forward-only spies trong script kiểm thử private; mọi call vẫn gọi service/provider thật và giữ nguyên kết quả. Không thêm framework observability hay log nội dung nguồn vào ứng dụng.

## Thay đổi đồng thời

Trong lúc làm việc, HEAD chuyển sang commit `32cdc36b` bởi hoạt động bên ngoài các thao tác của agent; commit đó đã chứa các thay đổi trước phiên và phần sửa đầu tiên. Agent không chạy stage/commit/push/reset, không đảo commit hoặc ghi đè thay đổi đồng thời. Diff so với HEAD cuối vì vậy không đại diện toàn bộ phần việc đã thực hiện trong phiên; red receipts và file hashes ghi nhận trạng thái kiểm thử.

Báo cáo, nhật ký và memory được thêm theo workflow repo. Không có frontend code trong phạm vi Context564; frontend build không chạy lại cho thay đổi Python này.
