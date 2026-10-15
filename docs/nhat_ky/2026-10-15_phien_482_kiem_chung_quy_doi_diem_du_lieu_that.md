# Nhật Ký Phiên 482 — Kiểm chứng công cụ quy đổi điểm bằng dữ liệu thật

- **Ngày**: 2026-10-15
- **Phạm vi**: Backend RAG (`score_conversion*`), `evidence_facts`, kiểm thử, script kiểm chứng read-only
- **Trạng thái bàn giao**: Engine đạt, dữ liệu thật đã kiểm chứng, **rule vẫn ở bản nháp — công cụ TẮT**

---

## 1. Mục tiêu phiên

Hoàn thiện **công cụ quy đổi điểm có kiểm chứng** trên nguồn thật
`docs/tai_lieu/tuyen_sinh/Thong_bao_quy_doi_tuong_duong_QNU_2026_Chinh thuc-signed.pdf`,
theo 4 cổng A (kiểm chứng dữ liệu đang phục vụ) → B (hoàn thiện engine) →
C (cấu hình có kiểm soát) → D (kiểm chứng). Ràng buộc giữ nguyên: không nhận
rule/bảng/bằng chứng "đã duyệt" từ request hoặc chat, không giả danh người duyệt,
không suy năm từ tên file, không ngoại suy/clamp/dùng bảng năm khác/số do LLM sinh,
không reparse/reindex/publish/reset DB/đổi ModelOps, không commit/push/deploy/restart.

## 2. Cổng A — Kiểm chứng dữ liệu đang phục vụ (đạt)

Phân giải lại publication hiện tại từ DB, **không dùng ID cũ làm giả định**. Kết quả trùng khớp
tham chiếu phiên 481 nên được phép tiếp tục:

| Thành phần | Giá trị thực đọc từ DB |
| --- | --- |
| Tenant / Workspace | `tenant_qnu` / `workspace_qnu` |
| Collection | `col_admissions` |
| Binding (active) | `bnd_e52fd3712ac3` |
| Source revision (ready) | `ks_rev_259de8772948`, revision_no 3 |
| Index revision (active) | `idx_rev_5f5f3f114ca1` |
| Canonical hash | `ddceee8b1442a36cb3359e2ce9f54850646384a3086be87c25e25a2c8bc9fd2f` |
| Origin file hash | `96207cca…5dc8e` |
| Chunks / Facts | 116 / 534 (parity 116/116) |
| Snapshot engine thấy | `snap_col_admissions_3_eba9386b` |

Bằng chứng truy hồi được khi ghim đúng binding đang xuất bản:
**41 canonical blocks + 72 fact blocks**, phân loại thành
**22 hàng lưới bách phân vị** (mỗi hàng 22 ô: `ĐNL` + 7 tổ hợp gốc × {SPT, HB, THPT})
và **50 hàng ánh xạ tổ hợp** (mỗi hàng 1 ô), **`unclassified = 0`** — không còn ô mồ côi.

Các bất biến đã đối chiếu trực tiếp trên dữ liệu thật:

- Cả 50 hàng ánh xạ dùng **một** nhãn cột gốc duy nhất `Tổ hợp gốc tương đương`
  và **một** nhãn cột mã duy nhất `Mã tổ hợp`; 50 mã **không trùng lặp**.
- `entity_name` của hàng ánh xạ là **danh sách môn**, `entity_code` là **NULL** →
  giả định "entity_name luôn là mã tổ hợp" của engine cũ là **sai với nguồn thật**.
- Phân bố mã theo tổ hợp gốc: A00:2, A01:5, B00:10, C00:10, C01:2, D01:15, D07:6 (tổng 50).
  Mã mới `A01` ánh xạ về gốc `A01` → oracle của người dùng biểu diễn được trực tiếp.
- **Phạm vi năm**: toàn bộ facts vẫn có `temporal_context.type = "unknown"`, `year = null`.
  **Không âm thầm sửa thành 2026.** Năm 2026 chỉ được chứng minh bằng trích dẫn canonical
  (block `ks_rev_259de8772948:827:958`), không suy từ tên file hay năm ban hành.
- Các mốc nguồn/đích của một cặp nội suy **luôn thuộc cùng một hàng bách phân vị**
  (cùng `block_id`), và cột nguồn/đích là hai cột đã duyệt riêng biệt.
- ĐNL và SPT được chứng minh là **hai kỳ thi khác nhau** bằng trích dẫn
  `ks_rev_259de8772948:1099:1277` → không tự gộp.

Tám trích dẫn canonical dùng làm bằng chứng quy tắc (mỗi anchor đúng **một** block):
`year_scope :827:958`, `interpolation :1912:2080`, `rounding :2416:2494`,
`base_combinations :1428:1783`, `mapping_annex :2496:2679`,
`source_marks :2167:2239`, `target_scale :2240:2322`, `distinct_source_exams :1099:1277`.

## 3. Cổng B — Hoàn thiện engine cho dữ liệu thật (đạt)

**Nguyên nhân gốc**: `score_conversion.py` đối chiếu danh tính tổ hợp bằng
`entity_name == request.combination`, trong khi nguồn thật đặt `entity_name` là danh sách môn;
đồng thời `reviewed_fact_blocks` **không đưa `row_context` vào evidence**, nên không có
đường nào đọc mã tổ hợp có provenance.

**Thuật toán thay thế (tổng quát, không hardcode từ vựng/bảng điểm)**:

1. `evidence_facts.py` đưa `row_context` (danh sách cặp `[nhãn_cột, giá_trị]` sinh ra từ chính
   header đã duyệt khi tái tạo bảng) vào `fact_context` của block hàng đã duyệt.
2. `ConversionRule` thêm trường **đã duyệt** `combination_context_attribute` — nhãn cột mã
   do người duyệt chỉ định, không phải hằng số trong code.
3. `reviewed_row_code(block, label)` khớp nhãn bằng chuẩn hóa NFC + casefold + gom khoảng trắng,
   yêu cầu **đúng một** ô khớp. Không khớp, trùng hai ô, context sai hình dạng (không phải cặp 2
   phần tử) hay thiếu → `ValueError`. **Không nới thành tìm chuỗi con tùy tiện.**

Cách này giữ nguyên tính tổng quát: bảng khác dùng tên môn, mã ngành hay nhãn nào khác làm định
danh hàng đều hoạt động, miễn nhãn đó được duyệt và khớp đúng một ô.

**Sửa bổ sung phát hiện khi chạy dry-run**: `convert_admission_score` gọi
`resolve_retrieval_snapshot` **ngoài** khối try/except, nên sự cố DB ở bước phân giải snapshot
trào ra thành lỗi 500 thô, không phải RFC 7807. Đã bọc lại, **cho `AppException` đi xuyên**
để từ chối phạm vi (404/403) không bị đội lốt "DB lỗi" (503).

Các chốt an toàn giữ nguyên và đã kiểm chứng lại: source/index/canonical_hash hiện hành,
cách ly tenant/workspace, không ngoại suy/clamp, đơn điệu nghiêm ngặt (trùng mốc → từ chối chứ
không tự sửa), cột đích không giảm theo cột nguồn, ô thiếu → không tự điền, `Decimal` prec 40
và **làm tròn đúng một lần cuối**.

**Chính sách làm tròn** (ghi rõ để không nhầm là câu chữ văn bản): văn bản quy định
*làm tròn một lần ở bước cuối đến hai chữ số thập phân*; còn **xử lý điểm giữa bằng
`ROUND_HALF_UP` là chính sách vận hành do người dùng xác nhận**, không phải câu chữ bổ sung
của văn bản. Không dùng thời điểm duyệt tài liệu làm bằng chứng người duyệt đã duyệt mọi cấu hình.

## 4. Cổng C — Cấu hình có kiểm soát (dừng ở bản nháp, công cụ TẮT)

`scripts/build_conversion_rules.py` **suy ra** toàn bộ cấu hình từ publication đang sống
(không gõ tay bảng điểm, không hardcode danh sách tổ hợp): thứ tự hàng lấy từ
`raw_data->>'row_index'` (giữ đúng thứ tự bách phân vị đã duyệt, **không sắp xếp theo giá trị**),
nhãn cột gốc/mã và tập tổ hợp gốc suy từ chính các ô, cột đích của mỗi gốc chọn theo hình thái
`tokens(cột)[:1] == [gốc] and phương_thức_đích in tokens(cột)[1:]`; mọi mơ hồ/trùng mã → **dừng**,
không tự chọn. Script **tự hủy nếu publication đã đổi** so với tham chiếu phiên 482.

Kết quả bản nháp: **7 rule** `qnu-2026-ĐNL-{A00,A01,B00,C00,C01,D01,D07}-THPT`,
mỗi rule 22 mốc, tổng 50 mapping, 8 `rule_proofs` canonical, `source_attribute="ĐNL"`,
`target_attribute="<GỐC> / THPT"`, `combination_context_attribute="Mã tổ hợp"`, `year=2026`,
`decimal_places=2`, `rounding="ROUND_HALF_UP"`, `operation="piecewise_linear"`, ghim đúng
binding/index/source/canonical_hash đang xuất bản.

Tự kiểm chứng chéo (công thức được cài **độc lập lần hai** để đối chiếu, không dùng lại
đường runtime): **634 check, 0 lỗi** (75/85/99/99/75/114/87 theo từng rule), gồm quét toàn bộ
mốc, mẫu biên, dò nội suy, ngoài khoảng, 6 đột biến phủ định và oracle công bố.

**Không kích hoạt.** `reviewed_by` đang là `"pending-operator-review"`, `mode="draft"`,
`writes=0`. Lý do: kích hoạt là hành động quản trị cần **danh tính người duyệt thật**, và
ràng buộc phiên cấm giả danh người duyệt. Theo đúng điều khoản "nếu quyền ghi cấu hình hoặc
nguồn chưa đủ điều kiện thì báo rõ và giữ công cụ tắt", công cụ **vẫn TẮT**. Lệnh kích hoạt
khi có người duyệt:

```bash
python -m scripts.build_conversion_rules --activate --reviewed-by "<danh tính người duyệt thật>"
```

Ghi cấu hình đi qua cơ chế quản trị server-trusted hiện có
(`PUT /knowledge/collections/{id}`, quyền `ai.knowledge.update`, service gộp `metadata`
giữ nguyên các khóa khác) — **chỉ ghi phần `score_conversion_rules`**, không đụng metadata khác.

## 5. Cổng D — Kiểm chứng (đạt)

**Regression viết trước, thấy đỏ rồi mới sửa.** `tests/test_score_conversion.py` viết lại:
**68 test pass**. Các nhóm phủ:

- Số học & làm tròn: đúng mốc, giữa mốc, đầu/cuối khoảng, HALF_UP tại đúng điểm giữa
  (`24,125 → 24,13`, và HALF_EVEN/DOWN cho kết quả khác để chứng minh mode có tác dụng),
  dấu phẩy thập phân (`"780,00"`), làm tròn cuối một lần, số mơ hồ/thực thi được
  (`NaN`, `Infinity`, `1,000`, `2e3`, `1/0`) bị từ chối.
- Oracle độc lập lấy từ Phụ lục công bố: **780 → 21.21**, cặp mốc `(764; 20,75)`–`(790; 21,50)`.
- Ngoài khoảng: `26.99` / `1024.01` / `2000` → `missing` + `SCORE_OUTSIDE_VERIFIED_RANGE`,
  không clamp, không ngoại suy.
- Danh tính tổ hợp: mã phải đến từ **đúng một** ô `row_context` đã duyệt — 7 biến thể xấu
  (rỗng, sai nhãn, sai mã, trùng, sai hình dạng, scalar, `None`) đều bị từ chối;
  `entity_name` là danh sách môn **không bao giờ** cấp quyền cho mapping; nhãn cột mã đã duyệt
  không khớp cột nguồn nào → từ chối.
- Toàn vẹn bằng chứng: ô bị đổi, mapping chuyển sang source revision khác, rule ghim index
  revision đã bị thay thế, mốc vay cột kỳ thi khác, hai mốc từ hai hàng bách phân vị khác nhau,
  mốc nguồn trùng, ô thiếu, `rule_proofs` không phải trích dẫn nguyên văn.
- Biên hệ thống: DB lỗi → `SCORE_RULE_UNAVAILABLE` (cả ở bước đọc rule **và** bước phân giải
  snapshot); thiếu rule → `missing` chứ không thành đáp án giả; collection lạ → 403;
  snapshot lệch phạm vi → `SCORE_SCOPE_FORBIDDEN` và **không đọc rule**; router lấy
  tenant/workspace từ **actor**, không từ body; chat **không để LLM viết lại kết quả số**
  và không được model "bổ sung" điểm/năm thiếu từ câu hỏi gốc.

**Chấp nhận end-to-end trên publication thật** (`scripts/verify_conversion_dry_run.py`,
read-only, quy tắc nháp bơm qua proxy session, **0 ghi DB, 0 gọi model**):
**26/26 case pass, 0 lỗi**.

| Case | Kết quả thật |
| --- | --- |
| Oracle công bố `A01 / 780` | **21.21**, bracket `764→20.75` … `790→21.5`, 11 citations |
| Midpoint HALF_UP `A01 / 777` | **21.13** (21.125 đúng điểm giữa) |
| Đúng mốc `790` / `764` | 21.50 / 20.75 |
| Mốc cao nhất / thấp nhất | 28.25 (`1004→1024`) / 5.35 (`27→432`) |
| Dấu phẩy thập phân `780,5` | 21.23 |
| Mã ánh xạ `X26` (gốc A01) | 21.21 — đồng nhất với gọi trực tiếp `A01` |
| Mã ánh xạ `A02` (gốc A00) | 22.56 — dùng đúng cột gốc A00, không vay A01 |
| 5 gốc còn lại tại 900 | B00 25.64, C00 23.14, C01 24.06, D01 23.56, D07 23.89 |
| Ngoài khoảng `26` / `1025` | `SCORE_OUTSIDE_VERIFIED_RANGE` |
| Sai năm 2025; nguồn SPT/THPT/HB; `A03`; `ZZ99` | `NO_VERIFIED_CONVERSION_RULE` |
| Alias `ĐGNL` / `đánh giá năng lực` | 21.21 (khớp alias đã duyệt) |
| DB lỗi | `SCORE_RULE_UNAVAILABLE`, không ra đáp án |
| Tenant lạ | bị từ chối (404, không lộ sự tồn tại của collection) |

Mỗi kết quả `calculated` mang **11 citations / 11 evidence blocks** (2 hàng mốc + hàng mapping
+ 8 bằng chứng canonical) — không có đáp án nào thiếu trích dẫn.

**Quality gate cuối phiên**:

- `uv run ruff check .` → **All checks passed!**
- Focus `tests/test_score_conversion.py` → **68 passed**
- Full backend → **11 failed / 1604 passed / 16 skipped / 0 errors**.
  **11 ID lỗi trùng khớp tuyệt đối baseline** (consulting dispatcher ×2, publishing cutover/GC ×2,
  decommissioning & system GC ×3, canary/rollback ×1, RAG reconciliation ×1,
  auth session claims ×1, universal tools ×1). Không sửa lan, không bỏ assertion để làm xanh.
  Số pass tăng đúng bằng số test mới thêm.
- Ghi chú môi trường: 54 lỗi `PermissionError` trên `Temp\pytest-of-AnhTuan` ở lần chạy trước là
  **hỏng ACL Windows ngoài repo**, không do thay đổi phiên này; chạy với
  `--basetemp=storage/pytest-basetemp-482` thì hết hẳn (0 errors). Không xóa/chmod gì của hệ thống.

## 6. Thay đổi tệp

| Tệp | Hành động | Mô tả |
| --- | --- | --- |
| [app/modules/rag/evidence_facts.py](../../backend/app/modules/rag/evidence_facts.py) | Sửa | Đưa `row_context` có provenance vào `fact_context` của hàng đã duyệt |
| [app/modules/rag/score_conversion_schemas.py](../../backend/app/modules/rag/score_conversion_schemas.py) | Sửa | Thêm `combination_context_attribute` (bắt buộc) vào `ConversionRule` |
| [app/modules/rag/score_conversion.py](../../backend/app/modules/rag/score_conversion.py) | Sửa | `reviewed_row_code()`; đối chiếu mã tổ hợp theo ô đã duyệt; bọc lỗi snapshot thành 503 RFC 7807 |
| [tests/test_score_conversion.py](../../backend/tests/test_score_conversion.py) | Viết lại | 68 test: oracle độc lập, làm tròn, danh tính tổ hợp, toàn vẹn bằng chứng, biên hệ thống |
| [scripts/build_conversion_rules.py](../../backend/scripts/build_conversion_rules.py) | Mới | Suy 7 rule từ publication sống + tự kiểm chứng chéo; chỉ ghi khi có `--activate --reviewed-by` |
| [scripts/verify_conversion_dry_run.py](../../backend/scripts/verify_conversion_dry_run.py) | Mới | Chấp nhận end-to-end read-only, 26 case, 0 ghi / 0 model |
| [scripts/inspect_conversion_482_shape.py](../../backend/scripts/inspect_conversion_482_shape.py) | Mới | Thăm dò hình dạng bảng thật (lưới/mapping/khác) |
| [scripts/inspect_conversion_482.py](../../backend/scripts/inspect_conversion_482.py) | Sửa | Chỉ sửa lint (SIM118, S112, FURB157) |
| `storage/rag_conversion_482/` | Mới | Bằng chứng kiểm toán: `shape_probe.json`, `reviewed_policy.json`, `conversion_rules.json`, `verification_report.json`, `acceptance_dry_run.json`, `full_suite_482*.txt` |

## 7. Giới hạn còn lại (báo rõ, không che)

1. **Công cụ đang TẮT**: chưa có rule kích hoạt vì thiếu danh tính người duyệt thật.
   Đến khi đó endpoint vẫn trả `NO_VERIFIED_CONVERSION_RULE`.
2. **Chưa có UI quản trị rule** và **chưa đăng ký vào Tool Gateway function-calling**;
   hiện chỉ dùng được qua endpoint có xác thực.
3. **Alias nguồn chỉ có 2** (`đánh giá năng lực`, `đgnl`) — đủ cho cách gọi trong văn bản,
   chưa bao phủ mọi cách nói của thí sinh.
4. **Chỉ hỗ trợ ĐNL → THPT** cho 7 tổ hợp gốc năm 2026. SPT/HB làm nguồn, các năm khác,
   tổ hợp không có trong Phụ lục 2 → trả trạng thái thiếu, **không suy đoán**.
5. **Chưa chạy bộ 82 câu**, chưa benchmark, chưa test model thật (không đổi cấu hình
   production để test; nếu cần thì chỉ dùng model nội bộ trên server AI và chặn mọi đường
   fallback/redirect ra cloud trước transport).
6. **Cần BE/worker nhận code mới** (`evidence_facts`, `score_conversion*`) thì thay đổi mới có
   hiệu lực runtime. **Không tự restart.**

## 8. Đề xuất bộ 20 câu đại diện (trong 82 câu) để kiểm tra tiếp

Mười câu đầu kiểm công cụ quy đổi (đã có oracle đối chiếu độc lập), năm câu kiểm ranh giới
từ chối, năm câu kiểm công cụ không phá luồng RAG sẵn có:

1. ĐNL 780 tổ hợp A01 quy đổi sang điểm THPT được bao nhiêu? *(oracle 21.21)*
2. ĐNL 777 A01 thì bao nhiêu? *(midpoint HALF_UP 21.13)*
3. ĐNL 790 A01? *(đúng mốc 21.50)*
4. ĐNL 27 A01? *(mốc thấp nhất 5.35)*
5. ĐNL 1024 A01? *(mốc cao nhất 28.25)*
6. ĐNL 780 tổ hợp X26? *(X26 = gốc A01 → 21.21)*
7. ĐNL 780 tổ hợp A02? *(A02 = gốc A00 → 22.56, không được vay cột A01)*
8. ĐGNL 780 A01? *(alias → 21.21)*
9. ĐNL 900 tổ hợp B00 / D01? *(25.64 / 23.56)*
10. ĐNL 780,5 A01? *(dấu phẩy thập phân → 21.23)*
11. ĐNL 1025 A01? *(ngoài khoảng → từ chối, không ngoại suy)*
12. ĐNL 780 A01 năm 2025? *(sai năm → thiếu rule)*
13. Điểm SPT 780 quy đổi sang THPT? *(kỳ thi khác → thiếu rule, không gộp)*
14. ĐNL 780 tổ hợp A03 / ZZ99? *(không có trong Phụ lục 2 → thiếu rule)*
15. Công thức quy đổi điểm giữa các phương thức năm 2026 thế nào? *(câu lý thuyết → trả trích dẫn,
    **không** kích hoạt máy tính, **không** sinh số)*
16. Điểm chuẩn ngành 7480107 năm 2026 là bao nhiêu? *(luồng facts sẵn có không bị ảnh hưởng)*
17. Tổ hợp A01 gồm những môn nào? *(liệt kê từ nguồn, không dùng bảng quy đổi)*
18. Học phí năm học 2026-2027 của trường? *(câu ngoài phạm vi công cụ, kiểm không nhiễu)*
19. Liệt kê toàn bộ tổ hợp xét tuyển thuộc nhóm gốc D01? *(15 mã, không bị TopK cắt)*
20. Quy đổi điểm giúp mình với? *(thiếu đầu vào → hỏi lại, không tự điền điểm/tổ hợp/năm)*

Tiêu chí đạt: câu 1–10 khớp oracle; câu 11–15 trả đúng trạng thái từ chối/thiếu kèm hướng dẫn,
tuyệt đối không có con số bịa; câu 16–20 không hồi quy so với kết quả phiên 475–476.

## 9. Bài học rút ra

- **Đừng tin tên trường, hãy đọc ô có provenance.** `entity_name` nghe như định danh nhưng nguồn
  thật đặt danh sách môn vào đó. Mọi đối chiếu danh tính phải đi qua ô/cột đã duyệt.
- **Test mock che được một nửa đường lỗi.** `test_tool_database_outage_is_not_no_answer` patch
  `resolve_retrieval_snapshot` nên không bao giờ chạm bước phân giải snapshot thật; chỉ dry-run
  trên DB sống mới lộ ra lỗi 500 thô.
- **Bản nháp + lệnh kích hoạt tách bạch** là cách giữ công cụ tắt mà không mất công sức kiểm chứng:
  mọi thứ đã sẵn sàng, chỉ thiếu đúng một danh tính người duyệt thật.
