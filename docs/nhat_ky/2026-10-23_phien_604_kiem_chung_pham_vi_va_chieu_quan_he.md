# Phiên604 — Phạm vi nguồn/năm, hướng quan hệ và coverage

Ngày 23/10/2026. Tiếp tục theo thứ tự đã thống nhất trước đợt5; P10 để sau.

## Phạm vi và phương pháp

- Đọc AGENTS/rules/memory, working tree và compiler603; giữ thay đổi600–603 chưa commit. Không subagent.
- Policy v3: literal scope, entity cùng nguồn, section một nguồn/profile năm, role phiên bản event, navigation status không thành authored status.
- Dựng chiều relation độc lập từ raw proof; supersedes mới → cũ. Hai đầu dùng membership map tránh model hiểu thứ tự mảng là chiều đề xuất.
- Coverage phân biệt missing fact/context/unrelated/unresolved qua hai lượt cùng model; bảo toàn review gốc, repair một gói, association chưa đồng thuận candidate_only.
- Enum references/handles mọi bước, exact wire budget, ledger primary/context, raw qualifier views và source-group synthesis. Không nâng call/time budget hoặc hạ gate.
- Tám file app khác snapshot đầu604,52 test IDs mới và ba test/fixture cũ thích ứng hợp đồng. Không parser/RAG/P10/FE/schema DB/model config thay đổi.

## Kiểm chứng thực chạy

DB/MinIO/Qdrant local xác minh trước chạy. DB604 riêng có nonce, LocalStorage riêng; Pytest network guard và endpoint ngoài127.0.0.1:1. Không migration DB ứng dụng.

| Kiểm tra | Kết quả | Exit |
|---|---|---:|
| Full baseline snapshot đầu604 | 3468 PASS /18 FAIL /17 SKIP, +23 subtest PASS | 1 |
| Bốn repro trước sửa | 4 FAIL đúng lỗi nghiệp vụ | 1 |
| Focused cuối | 138 PASS | 0 |
| Ruff12 file | PASS | 0 |
| Full cuối | 3520 PASS /18 FAIL /17 SKIP, +23 subtest PASS | 1 |
| Exact IDs/cause | 52 test mới PASS;0 failure ID mới/đổi cause/mất ID | 0 |
| Source/config/vector postcheck | Giữ bytes/seals/payload2943,0retrievable | 0 |
| Browser/chatbot64/FE | NOT RUN | — |

Full cuối chạy một lần sau batch ổn định,564,20s.18 lỗi nền vẫn FAIL; không ghép focused thành full PASS. Commands/cwd/argv/exit, JUnit/log tại `backend/storage/context604/checks/`; bảng IDs đầy đủ trong báo cáo.

## Thử compiler thật và kết luận

Cùng ba DOCX2024/2025/2026 và canonical parser602; source fixture chỉ format-only, chưa fresh parsing/full Quality Gate. Giữ Luna primary, fallback config không đổi,0fallback thực tế.7 build phát triển có224 usage success, receipts từng lỗi giữ riêng. Không resend uncertain intent.

Artifact cuối `kc_777596862bcf4bd8be4dac337131b75d`: create/exactGET200,10 assertions/3 sections/1 relation,41Luna success.381/381proof/canonical/binding/render/hash khớp.2024 không mượn Dự thảo2025;5948/1613 giữ điều kiện; publication2023 tách data2024;5.173→4.500 đúng; version18/09/2026 là event.24proof cũ đã đối soát exact span/vai trò, không phải24quota thiếu.

**Chưa APPROVED nội dung**:3 bất đồng topic relevance (chú giải X, tiêu đề ngày trống, quota bổ sung) vẫn chặn. Direction reviewer lượt7 nhầm thứ tự endpoint; code cuối sửa membership và regression đạt, nhưng probe thật cuối bị provider ReadTimeout/ALL_PROVIDERS_UNAVAILABLE.0 usage success row ở probe không phải0 request. Không relabel artifact7 hoặc gọi whole workflow PASS.

DB604 đã dọn bằng exact name/nonce. Storage giữ chứng cứ do policy recursive deletion đã chặn từ phiên trước; không lách guard. Shared5collections/24bindings/12source revisions/37index revisions/5assistants/13model configs giữ seals; không nguồn/model/index/publication writes, không restart/deploy/commit/stage/push/reset.

## Bàn giao

- [Triển khai](../bao_cao/context604/IMPLEMENTATION_REPORT.md)
- [Kiểm chứng và blocker](../bao_cao/context604/VALIDATION_REPORT.md)
- [Exact test IDs](../bao_cao/context604/TEST_ID_COMPARISON.md)
- [Vai trò24proof](../bao_cao/context604/RECONCILIATION_24.md)
- [Quy trình hiện hành](../quy_trinh/18_bien_soan_chu_de_nhieu_nguon.md)

Chưa rollout UI/serving đợt5 bằng artifact còn blocker. Cần xác định association/relevance ba proof và kiểm direction khi provider đáp ứng; không reparse/reindex hoặc đổi model để xóa cảnh báo. Điểm59/60 của602 là lịch sử, không phải kết quả604.
