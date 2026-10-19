# Context558 — Kết quả kiểm chứng

## Kết luận

Luồng Automatic Ingestion đạt các kiểm tra tập trung và không thêm lỗi so với Context557. **Full regression vẫn FAIL**, không báo toàn bộ hệ thống PASS: 2.466 PASS / 18 FAIL / 17 SKIP, 23 subtest PASS, exit 1, 476,60 giây. 37 test ID mới đều PASS; mọi ID chung giữ trạng thái; 18 lỗi giữ nguyên cả ID lẫn failure message. Xem [bảng từng ID](REGRESSION_IDS.md) và [đối chiếu máy đọc được](regression-comparison.json).

## Môi trường an toàn

Trước chạy đã xác minh cấu hình development/local DB 127.0.0.1:5432, MinIO 127.0.0.1:9000, Qdrant 127.0.0.1:6333. Các truy vấn kiểm tra nguồn thật dùng transaction READ ONLY. Regression chỉ dùng database riêng `qnu_test_context548_894b0d7658b6`, ownership nonce của runner, Storage local riêng `backend/storage/context548-runtime-894b0d7658b6/objects`; MinIO/Qdrant/Redis đặt localhost:1 để không truy cập dịch vụ thật. Auto migration/seed tắt. ORM chỉ tạo bảng trong DB test riêng; không migration production.

Runner tái sử dụng của Context548; tên runtime không phải dữ liệu Context548 đang phục vụ. Đã copy cấu hình resolver ModelOps và credential mã hóa vào DB test cho compatibility tests, không xuất bí mật. Không gọi lại LLM hoặc 22 packet, không gọi embedding provider thật.

## Các lượt chạy

| Lượt | Kết quả | Exit | Ghi chú |
|---|---|---|---|
| legacy-baseline | 70 PASS | 0 | Ba module lifecycle/scope/import trước triển khai |
| focused-baseline (Smart) | ERROR collection | 2 | Feature/module mới chưa tồn tại; không gọi là PASS |
| automatic-red | ERROR collection | 2 | Test viết trước implementation, module automatic_ingestion chưa tồn tại |
| ingestion-focused | 265 PASS + 23 subtest PASS | 0 | Native parsers, serving, upload/reparse, vector, selected publication, semantic lifecycle, Smart Approval |
| automatic-evidence | 12 PASS | 0 | Sau bổ sung đối chiếu raw unknown đi qua RAG source_rows; được full run cuối bao phủ lại |
| ingestion-full-final | 2.466 PASS / 18 FAIL / 17 SKIP + 23 subtest PASS | 1 | So sánh chính xác Context557; 0 lỗi mới |
| Frontend semantic-review-preview.test.mjs | 28 PASS | 0 | Bao gồm main ingestion panel, advanced optional, loading/error/single-flight/permission |
| Frontend vector-workflow/source-query-cache/clean-content | 13 PASS | 0 | Flow vector và cache hiện có |
| Biome scoped 9 file / LF | PASS | 0 | Không sửa file ngoài phạm vi |
| Ruff scoped 17 file | PASS | 0 | Backend thay đổi và 3 module test mới |
| Frontend build + TypeScript | PASS | 0 | Build cuối sau thay đổi UI |
| Fixture probes | PASS | 0 | 18 issue, 6 related reference, A03/A10/A11/A12, 3 ô đối chiếu XML; không ghi nguồn thật |
| Shared-source integrity cuối | PASS | 0 | Revision/binding nguyên vẹn; source hash và MD/JSON pair hợp lệ; không auto certificate retroactive |

Hai lượt full-final/full-verified trước điều chỉnh mục tiêu đã bị dừng khi chuyển phạm vi; không có kết quả đầy đủ và không được tính PASS. Các lỗi red/trung gian được giữ trong evidence, không thay thế bằng kết quả cuối.

## Kiểm chứng hành vi thực chất và giới hạn

- DOCX thật tạo từ dữ liệu test độc lập: parser native → chuẩn QNU MD/JSON → PostgreSQL và Local Storage thật. Digital PDF thật qua trích xuất offline và QC. Không dùng lại toàn tài liệu thật để tạo kết quả.
- Ô `/`, blank và `0` tách biệt; raw vẫn giữ, không thành fact chắc chắn; trường unknown còn nguyên khi RAG đọc row metadata từ chunks DB.
- Proposal pending chỉ lưu đề xuất: graph, facts, bảng và retrieval units có hiệu lực không đổi; vẫn tạo chunks cho nội dung đã chứng nhận.
- Bản mất bảng, không đọc được, canonical/source/hash thay đổi hoặc QC failed bị chặn. Native footnote chỉ giảm page warning khi có locator Word và neo được xác minh.
- Staging vector đi qua service và DB/Storage thật; chỉ indexer/parity adapter ngoài được thay bằng test adapter. Points là staging và không retrievable; active_index và collection epoch không tự đổi.
- Smart Approval riêng có ASGI permission, actor test, idempotency, hai kết nối PostgreSQL cạnh tranh, commit/storage failure và snapshot persistence. Không dùng actor test để duyệt proposal của người dùng thật.
- UI runtime chỉ đọc trang nguồn Context557: trạng thái cần kiểm tra, Markdown, vector disabled đúng và đối chiếu nâng cao. Không nhấn Approve, reparse hoặc Nạp vector. Đây không phải E2E upload → provider vector thật → publish → chatbot.
- Real LLM/embedding/Qdrant E2E và human SSO: **NOT RUN**. Mock adapter không được báo thành E2E PASS. 17 test SKIP giữ nguyên, không gọi PASS.

## Lệnh tái lập

Từ root repo, sau khi tạo một môi trường test sở hữu riêng mới bằng runner:

```powershell
backend/.venv/Scripts/python.exe backend/scripts/context_patch_validation.py run --state-file backend/storage/context558/isolation.json --audit-file backend/storage/context558/safety.json --evidence-dir backend/storage/context558/tests --label ingestion-full-final
```

Lượt focused dùng cùng runner với 13 module ghi trong `backend/storage/context558/tests/ingestion-focused-run.json`. Lệnh thực tế, cwd, endpoint test, exit, JUnit ID và lỗi từng lượt được lưu ở `backend/storage/context558/tests/*-run.json`, `*.xml`, `*.log`. State hiện đã dọn DB, nên không chạy lại lệnh với state cũ; phải tạo state sở hữu riêng mới và label evidence mới.

Từ frontend:

```powershell
node --test src/features/knowledge/components/semantic-review-preview.test.mjs
node --experimental-strip-types --import ./src/app/auth/test-loader.mjs --test src/features/knowledge/utils/vector-workflow.test.ts src/features/knowledge/utils/source-query-cache.test.ts src/features/knowledge/utils/clean-content.test.ts
npm run build
```

## Cleanup và dữ liệu thật

DB test đã xóa sau xác minh tên/nonce/ownership; không còn credential test trong DB. Storage runtime riêng còn **2.226 file / 32.290.795 byte**: bộ kiểm duyệt tự động chặn lệnh PowerShell xóa đệ quy theo chính sách trước khi lệnh chạy. Không thử shell/đường xóa khác, không tắt bảo vệ. Inventory và lý do ở `backend/storage/context558/cleanup.json`; state là `database_removed_storage_pending`. Các runtime cũ Context553–557 không bị đụng tới.

Evidence/checkpoint riêng trong Context558 giữ lại để truy vết. Context552–557 và dữ liệu nguồn thật không được sửa; final-integrity đối chiếu đầy đủ mọi cột của đúng revision/binding với snapshot trước phiên, pair/hash kiểm tra lại bằng Storage chỉ đọc. Không chứng nhận lại toàn database hoặc corpus ngoài phạm vi. Proposal thật vẫn changes_requested; active source/index của binding vẫn null. Không commit, push, restart, deploy, cấu hình model hoặc tự xuất bản.
