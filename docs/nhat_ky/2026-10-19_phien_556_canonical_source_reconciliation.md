# Phiên 556 — Canonical Source Reconciliation

Ngày 2026-10-19. Triển khai prompt Context556 theo phạm vi người dùng đã giao: audit nguồn, tái hiện khác hash, mapping không LLM, kiểm chứng nhập có xác thực trong môi trường test. Không sửa canonical cũ, tự duyệt hoặc ghi ứng dụng thật.

## Kết luận và nguyên nhân

**RECONCILIATION_BLOCKED.** DOCX offline và snapshot thật cùng SHA256 và 102.423 byte. Revision `ks_rev_84c4950c9ce2` của `bnd_21c09bbc6ca0` ở `col_admissions` ghi normalizer v16. Builder lịch sử tham chiếu `2cde271f` tái hiện đúng 299 core records bản lưu; builder hiện tại với native DOCX evidence tái hiện đúng 233 core records offline. Bản cũ materialize rich-cell paragraph vào prose và thiếu cả ba footnote, làm IDs dịch. Không đủ bằng chứng khẳng định chính xác toàn Git/dependency deployment cũ. MD/JSON khác nội dung và cấu trúc, không chỉ encoding/metadata.

11/12 assertion map bằng exact body, locator, ancestry/role và table raw/state grid; A12 thiếu footnote 2. Cột c02 của A12 cũng có header role metadata khác do label ô gộp; không mặc định đã xác minh role. A03 workflow nhóm A/2027 giữ nguyên, không c10–c12; AM-0007/AM-0070 và nhóm B không lẫn. O03/O05 có body nhưng chứa đích A12 chưa map, O08 thiếu footnote; O04/O06/O07 map được. Không coi mọi reference chặn toàn Bảng 1.

Stored projection còn replay mismatch 29 manifest diff với code hiện tại: `SEMANTIC_SNAPSHOT_INVALID / enrichment_structure`. Fresh projection chỉ phục vụ audit trong RAM, không cập nhật revision. Không tạo canonical import-package hoặc proposal hash giả. Offline555 vẫn đủ 12 assertion/18 issue, gắn offline544/draft544; revision thật stage mới 0 issue. Seals 14+5+5 file và ba manifest Context552/553/555 không đổi.

## Thay đổi

- Thêm công cụ offline `backend/scripts/reconcile_semantic_checkpoint.py`: mapping chính xác, hash/binding/ID mới khi nguồn đủ; chặn từng finding, không xuất proposal thiếu inventory; output không nằm trong checkpoint đầu vào, không ghi đè output tồn tại.
- Thêm `backend/tests/test_canonical_semantic_reconciliation.py`: 13 ca mới, gồm pending import/persistence với DB/Storage test.
- Không sửa runtime app/importer/guard/standard/parser. Báo cáo và bằng chứng sanitized ở `docs/bao_cao/context556/`; raw DOCX/MD/proposal chỉ giữ private Storage.

## Kiểm chứng thực chạy

- Baseline mới trước sửa: 80 PASS, exit 0. Red 11 FAIL vì chưa có module, exit 1.
- Focused sáu file: 146 PASS + 23 subtests PASS, exit 0.
- Native determinism: 1 PASS, exit 0; hai tiến trình, hai Storage riêng, cùng dependency/config/identity. PDF preview tắt ở cả hai, không suy full LibreOffice/PDF determinism.
- Historical core reproduction: 1 PASS, exit 0.
- Supplementary full-inventory: cuối 1 PASS, đủ 12 assertion/18 issue/6 reference, labels/roles giữ nguyên, proposal hash/source identity mới, không stage. Lượt đầu 1 FAIL do giả định probe sai rằng input_hash phải đổi chỉ do revision identity; sửa probe theo contract content/manifest/tables, không sửa runtime. Hai XML giữ riêng.
- Full backend một lần sau batch: **18 FAIL, 2.429 PASS, 17 SKIP, 23 subtests PASS, exit 1**. So với baseline full lịch sử Context555: đúng 18 failure ID và nguyên nhân đầu tiên, không ID bỏ/đổi trạng thái, 13 ID thêm đều PASS. Không gọi full suite PASS.
- Frontend preview 21 PASS; npm build gồm Vite + tsc --noEmit PASS; Ruff hai file PASS; Biome sáu file override LF PASS.
- CLI guard negative probe exit 1 đúng lỗi, không tạo file. Checksum cũ giữ nguyên. Probe CLI business exit 0 nhưng status RECONCILIATION_BLOCKED.
- Browser chỉ đọc tới SSO sign-in, chưa có session được cấp; UI_LIVE_NOT_RUN. Không dùng Dev Access Gate/token giả; không human/E2E.

Lệnh/cwd/exit code và exact test IDs nằm trong commands.json, VALIDATION_REPORT và regression-comparison.json. Chỉ format hai source file sau full, không thay hành vi.

## Môi trường, dọn dẹp và bước sau

DB/MinIO/Qdrant đã audit trước test. DB app chỉ đọc transaction READ ONLY; Storage chỉ GET. Test dùng DB nonce/ownership riêng, LocalStorage riêng, MinIO/Qdrant/Redis127.0.0.1:1, migrate/seed=false. Cấu hình ModelOps mã hóa copy đọc một chiều vào DB test cho cùng điều kiện regression, không in secret và không gọi LLM.

DB test đã dọn và xác nhận vắng. Runtime riêng `context548-runtime-09798fe46f29` còn 550 file/9.962.350 byte, 0links/0tracked/0process phù hợp. Remove-Item có guard bị kiểm duyệt tự động từ chối `blocked by policy`; không đổi công cụ xóa hoặc tắt bảo vệ. Không retry Storage cũ hay bản export ngoài repo đã bị chặn từ phiên trước. Checkpoint/audit/evidence giữ để đối soát.

Bước cần xác nhận theo prompt: tạo revision nháp mới bằng pipeline hiện tại, giữ bản cũ, chưa duyệt/index/publish. Kiểm lại worker và policy annotation trước dispatch; bản audit policy null và code bỏ qua inference khi null/disabled nên không cần LLM. Kiểm đủ footnote2, cột đích, pair hashes và projection rồi mới tạo proposal canonical mới và nhập có xác thực. Không live DB/revision/config/model/LLM/reparse/approve/index/publish/restart/deploy/commit/push trong556.

[Báo cáo cho người dùng](../bao_cao/context556/REVIEW_READY.md), [nguyên nhân](../bao_cao/context556/ROOT_CAUSE_REPORT.md), [kiểm chứng](../bao_cao/context556/VALIDATION_REPORT.md).
