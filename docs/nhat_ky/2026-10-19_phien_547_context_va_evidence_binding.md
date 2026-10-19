# Phiên 547 — Context có cấu trúc và evidence binding

## Yêu cầu và phạm vi

Thực hiện prompt structure-aware context expansion/evidence binding. Người dùng
cho phép baseline trước sửa với điều kiện kiểm DB/MinIO/Qdrant, dùng DB test và
Storage tạm, giữ exact ID/exit/cause trước-sau và dọn test data. Không commit,
push, migration production, sửa nguồn thật, reparse/index/publish/restart.

Áp dụng clean-code, ingestion, RAG pipeline, backend, ModelOps và frontend skills.
Không tạo subagent. Giữ toàn bộ thay đổi đợt1/2 chưa commit, không refactor RAG.

## Thực hiện

- Audit exact-quote failure lịch sử và tái hiện ranh giới bằng regression có kiểm
  soát; không giả raw model response cũ đã mất.
- Tạo DB test có nonce/ownership, Storage local tạm và dead endpoints cho dịch vụ
  dữ liệu; tắt auto migrate/seed. Shared DB chỉ SELECT READ ONLY cấu hình cho live.
- Thêm context/evidence/selector/ModelOps orchestration helpers, tái dùng annotation
  staging, snapshot/review/persistence hiện hữu. Không đổi Markdown Standard.
- Row directory giữ group xuyên windows; full field bắt buộc cho cell meaning.
  Header paths nằm ở columns, không lặp mỗi cell. Related budget/deferred IDs,
  exact references/ambiguity traces, on-demand row expansion và atomic stage.
- Backend tự cắt source quote, ghim source/revision/input/text hashes và code-point
  span. Không model-authored quote, fuzzy matching, sibling borrowing hay tự duyệt.
- UI chỉ bổ sung reason/source/span/unresolved trên preview đang có. Unknown và
  acknowledged-limits policy đợt2 không thay đổi. Runtime providers vẫn động từ DB.

Chi tiết file/hàm và giới hạn ngữ nghĩa:
[EVIDENCE_BINDING_IMPLEMENTATION](../bao_cao/context547/EVIDENCE_BINDING_IMPLEMENTATION.md).

## Kiểm chứng

Baseline cô lập18FAIL/2243PASS/17SKIP/0ERROR/23subtests, exit1. Red selector
1FAIL/1PASS trước implementation. Focused cuối127PASS,50,44s, exit0; Ruff12file,
frontend8behavior/Biome3file/build TypeScript PASS. Một full trung gian dừng chủ
động để giảm context lặp, không dùng làm kết quả. Full cuối **18FAIL/2264PASS/
17SKIP/0ERROR/23subtests**,360,23s,exit1; exact18IDs và first causes bằng baseline,
không test cũ biến trạng thái/bị mất,21case mớiPASS. Toàn suite vẫn FAIL.

Offline cùng DOCX checksum:19packets,0focal bị bỏ, tổng655.956bytes cả schema/system,
build486,03ms; overhead cao hơn catalog cũ75.884bytes, không báo cải thiện hiệu năng.
Live lượt đầu primary trả response nhưng expansion hết budget; sau sửa compact,
live cuối ALL_PROVIDERS_UNAVAILABLE/ReadTimeout. **E2E BLOCKED**, chưa valid proposal
thật/human review/apply/reload. Không đổi timeout/model để đạt PASS, không retry vô hạn.

Database/Storage cleanup: **DONE**, ownership check và SELECT xác nhận DB không
còn; runtime và6bản sao/object targets đã xóa, Test-Path đều false, cleanup exit0.
Dossier ignored giữ JUnit/run.json/ID-status-
cause/hash/trace/metrics; không lưu credential. Hướng dẫn, bảngT01–T17 và exact
regression IDs ở [VALIDATION_REPORT](../bao_cao/context547/VALIDATION_REPORT.md).

## Việc còn lại

Live vẫn cần provider ổn định và proposal hợp lệ rồi người dùng có quyền duyệt.
Code binding PASS không đồng nghĩa source537 hoặc các PDF cũ được duyệt.
