# Phiên 601 — Bảo toàn tiền đề và kiểm chứng nguồn nhiều năm

Ngày 22/10/2026, nhánh `v1.0.1`. Người dùng đồng ý triển khai hai ưu tiên tiếp sau
Wiki4–6: sửa nguyên nhân P07 và thử tài liệu thật2024/2025/2026. Giữ code600,
model/nguồn/Quality Gate; không commit/stage/push, reindex, publish, restart hoặc deploy.

## Thay đổi

- `backend/app/modules/rag/source_dependency_agreement.py`: một verdict not_required
  nhưng vẫn khẳng định prerequisite/exception/scope không được xóa nghĩa vụ nguồn
  mà source review đã yêu cầu; giữ ID/source/revision guard, restore và reverify.
- `backend/app/modules/rag/evidence_rule_selection.py`, gọi từ `evidence_claims.py`:
  offer toàn nhóm list native QNU cùng owner vào draft, có giới hạn; verifier/audit
  vẫn độc lập, không biến adjacency thành semantic approval hoặc fact.
- Hai file regression601:9 ca role/repair và14 ca selection/boundaries/verifier.
- Fixture `test_wiki_snapshot_integration_600.py` cho phép DB601 và kiểm comment
  owner, để kiểm DB/ASGI600 thực chạy trong isolation của601.
- Không thay app/parser/FE khác. App-before hash xác minh2 file app sửa,1 file mới,
  không file app bị xóa; các thay đổi600 của người dùng giữ.

## Kiểm chứng thực chạy

| Phép kiểm | Kết quả | Exit/giới hạn |
|---|---|---|
| Baseline role |4 FAIL đúng hành vi,2 PASS control|exit1; sau đó thêm3 cross-revision|
| Baseline source-group |1 FAIL thiếu sibling|exit1, trước sửa selection|
| Focused cuối34 file |852 PASS,1 warning|exit0; gồm DB/ASGI600 thật|
| Ruff6 file |PASS|exit0|
| Full cuối |3361 PASS,19 FAIL,17 SKIP,+23 subtestPASS|exit1; không mất testID|
| So full600 theo ID/cause |18 lỗi nền giữ,1 FAIL mới backupWindows|đối chiếu exit0, không phải PytestPASS|
| Backup chẩn đoán riêng |6 PASS|exit0; không thay19FAIL của full|
| Frozen64 cuối |57/60 tri thức;47/50positive,10/10negative,4/4social|target85 PASS, cònP07/P08/P16|
| Multi-source local adapters |4/12 PASS,8 FAIL|runnerexit0 hoàn thành12, acceptanceFAIL|
| Postchecks |source/config/code/vector giữ|exit0; không publication|

Full trước selection3348/18/17 giữ riêng. Lượt60164 trước selection56/60,
FAILP06/P07/P08/P13, cóP07EVIDENCE_TIMEOUT90s; không ghép vào lượt cuối.
600final59/60 là lịch sử cùng source/model/rubric; chốt601 giảm2 câu (P08/P16),
P07 vẫnFAIL ở nhánh chọn claim rỗng/không dùng được. Chưa có ablation lặp để
chốt mọi chênh lệch là do code; chưaAPPROVED hoặc sửa xongP07 ở E2E.

64chốt có128/128 citation resolve,149Luna/0fallback,0runtime. Chạy candidate
rag_service thật có actor/snapshot server kiểm quyền, không phải published HTTP E2E.
Các sự cố prepare trước run-intent có0inference, không resend uncertain requests.

## Thử nghiệm nguồn thật

3DOCX qua parser/QNU Markdown+JSON/canonical.2024 và2025 Wiki unavailable trước
inference do6unit ngắn; OOXML chứng minh5cửa sổ fragment cùng paragraph gốc.
2026 Wiki tạo4trang qua2Luna calls. Source canonical fallback thử12câu thật:
M03/M05/M06/M07PASS;M01/M02/M04/M08insufficient;M09–M12runtime scope invalid.
Probe cùng kế hoạch năm: câu chữ liền năm FAIL, whitespace controls PASS4/4,
0LLM; không đổi freeze hoặc thay kết quả. QA102usage+compiler2, chỉLuna,0fallback;
14/14citation resolve. Graph3structural links, không kiểm chứng đa nguồn co-mention.

Cẩm nang2025 dài kiểm riêng bằng compiler/selector xác định,0LLM:1301sections
vượt512 sau19gói. Không bỏ đoạn, tăng vô hạn limit, tự sửa nguồn hoặc giảready.
Không render Office/kiểm đủ ảnh; định dạngPASS không chứng minh đủ nội dung.

## Dữ liệu và dọn dẹp

Safety trước test:development DB/MinIO/Qdrant loopback. Pytest dùng DB sở hữu
`qnu_test_context601_3ef5959f23df`, local Storage và networkguard, không migrate
DB dùng chung. Sau hoàn tất xác minh exactname/nonce rồi drop đúng DB, exit0;
Storage/evidence giữ theo chính sách bảo vệ có từ trước, không thử xóa/bypass.
LLM usage audit giữ. Cả3bytes DOCX và PDF/revision/index/model/config không đổi;
2943vector payloads khớp nguyên,0retrievable, active index rỗng, chưa publish.

Báo cáo: [triển khai](../bao_cao/context601/IMPLEMENTATION_AND_VALIDATION.md),
[exact testIDs](../bao_cao/context601/TEST_ID_COMPARISON.md),
[nguồn nhiều năm](../bao_cao/context601/MULTI_SOURCE_EVALUATION.md).

Bước tiếp có bằng chứng: đối soát paragraph native và unit ngắn; nhận diện năm
sát chữ mà không nhầm mã; chia inventory Wiki có giới hạn; bổ sung trace an toàn
và xử lý selector/audit P07/P08/P16/M08. Không tự reindex các nguồn đang giữ.
