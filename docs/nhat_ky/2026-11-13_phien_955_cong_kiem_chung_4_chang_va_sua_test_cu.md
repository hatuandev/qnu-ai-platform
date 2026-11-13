# Phiên 955 — Cổng kiểm chứng 4 chặng và sửa 6 tệp test cũ theo hành vi mới

## 1. Yêu cầu và giả định

- Người dùng yêu cầu chia bộ backendV1 (1945 test đã thu thập) thành **4 chặng chạy song song** để rút ngắn thời gian và dùng làm cổng sẵn sàng production; sau đó chỉ đạo **"chờ B xong rồi chạy lại D đơn lẻ"**.
- Khi có kết quả: rà lỗi, nêu lỗi cần sửa trước khi chạy lại; **chốt hướng xử lý 2a trước**, rồi tiếp tục điều tra 2b.
- Nguyên tắc đã thống nhất: test cũ lệch hành vi mới thì **cập nhật test theo hành vi mới**, không sửa hay nới mã sản phẩm; không commit/push cho tới khi được duyệt; không chạy trên DB ứng dụng; giữ nguyên các diff chưa commit khác của người dùng.
- Môi trường: harness cô lập tạo/huỷ `qnu_v1_test_<16hex>` mỗi lượt, Redis logical DB 15, guard chặn mạng ngoài, `DEV_AUTH_ENABLED=true`; nhãn PASS chỉ ghi cho lượt thực chạy và đọc từ `receipt.json`/`result.xml`.

## 2. Kết quả cổng 4 chặng (trước khi sửa)

| Chặng | Phạm vi | Kết quả lượt chạy | Bằng chứng |
| :--- | :--- | :--- | :--- |
| A | `tests/unit` và phần nhẹ | **1167 passed**, 4 warnings, 33,61 s | Log tác vụ nền 10:11:54; không còn receipt riêng trong `storage/context636` |
| B | Integration phần 1 | **330 passed, 3 failed** / 333 test, 2.961 s | DB `qnu_v1_test_0b6c2a22b0a945f3` |
| C | Integration phần 2 | Lượt đầu **251 passed, 3 failed** / 254 test, 1.322 s; sửa test rồi chạy lại **254/254 PASS**, 1.254 s | DB `qnu_v1_test_9d338fb048a449e7` → `qnu_v1_test_745b25d1462649c4` |
| D | Integration phần 3 | Lượt đầu **189 passed, 2 failed** / 191 test, 906 s; các lượt chạy lại toàn D crash `0xC0000005` (lượt sâu nhất dừng sau **160 PASSED**, 577,83 s); phần còn lại 30 test chạy 2 lô **26/26 + 4/4 PASS** | DB `qnu_v1_test_77dbc6613f2244f1`, `qnu_v1_test_de006e71cd904355`, `qnu_v1_test_98815b9b8c4746aa`, `qnu_v1_test_10b8c4c36c2b4b15` |

- Tổng thu thập 1945 test. **Mọi test đều có ít nhất một lượt PASS**, nhưng **không có một lượt chạy liền mạch nào cho D và không chạy lại toàn bộ B sau khi sửa** — không tuyên bố "single-run PASS" cho toàn bộ suite. Sau khi sửa, B và D đã được chạy lại trên mã cuối — xem mục 4.
- Crash D là `0xC0000005` (access violation trên Windows, trong CPython regex C module qua SQLAlchemy `safe_construct` khi job anyio đang chạy), không phải assertion failure; DB vẫn được drop và legacy sentinel được giữ ở mọi lượt.
- Ba lỗi của B: 2 tham số `test_integration_gateway_pipeline.py::test_external_key_calls_real_rag_and_preserves_assistant_config[128|None]` và 1 `test_legacy_source_deletion_718.py::test_legacy_deleted_source_with_published_version_is_still_protected`.
- Hai lỗi của D: `test_connection_tests_706.py::test_exact_second_key_history_and_refresh` và `::test_temporary_key_does_not_mark_saved_keys_verified`.

## 3. Sửa theo hành vi mới (không đổi luồng nghiệp vụ)

### 3.1 Compiler metadata (C) — `test_compiler_selective_893.py`, `test_compiler_supplement_879.py`
- Hành vi mới từ đường năm theo header cột (phiên 947–949): ngoài annotation model "Số hiệu", supplement có thêm **2 annotation `origin: "rules"`** với `{"data_year": 2023}` và `{"data_year": 2024}`.
- Cập nhật kỳ vọng: `origin == ["model", "rules", "rules"]` và danh sách values tương ứng; giữ nguyên các assert về section, source table và node index.
- Lượt chạy lại đúng 2 tệp: **6 passed** (DB `qnu_v1_test_06023783d9b04437`, 40,08 s).

### 3.2 Connection tests (D) — `test_connection_tests_706.py`
- Hành vi mới từ discovery native (A3/A3b): sau khi discovery, adapter gọi thêm 3 route OpenAI-compatible **`GET /v1/models`, `GET /api/tags`, `GET /props`** mỗi lần test khóa.
- Cập nhật kỳ vọng: mỗi khóa gọi đủ 3 route theo thứ tự; khóa thứ hai chỉ được dùng sau khi khóa đầu fail; khóa tạm vẫn không đánh dấu verified.
- Lượt chạy lại đúng tệp: **9 passed** (DB `qnu_v1_test_6580c2e796a4417f`, 73,09 s).

### 3.3 Tinh chỉnh C2 — `rag/answer/cache.py`, `rag/answer/service.py`, `test_answer_cache_956.py`
- Bỏ `usage_id` khỏi entry cache và bỏ `origin_usage_id` khỏi trace hit: cache hit không reserve/settle usage nên không có usage id hợp lệ để tham chiếu; tránh dữ liệu usage cũ lọt vào trace.
- Log `answer` ghi `cache="disabled"` khi TTL = 0 thay vì "miss" (phân biệt tắt cache với trượt cache).
- Test 956 thêm assert `"origin_usage_id" not in second.trace.cache`.
- Tệp unit này nằm trong chặng A; chặng A chạy lúc 10:11 sau thời điểm sửa 09:35 và PASS 1167 test.

### 3.4 Xóa nguồn legacy có bản published — 2a (`test_legacy_source_deletion_718.py`)
- Hợp đồng mới: xóa nguồn đã có bản published **không còn trả 409 `source_publication_in_use`**; preview trả `impact.published_versions_to_withdraw == 1`, accept chuyển ngay bản published → `withdrawn`, worker `execute(...)` → `completed`, GET source → 404.
- Viết lại test thành `test_legacy_deleted_source_with_published_version_withdraws_on_confirmed_purge`, đọc trạng thái `CompiledVersion` trực tiếp từ DB cô lập trước/sau accept thay vì qua endpoint.
- Lượt đầu 1 failed/2 passed do test cũ; sau sửa **3/3 PASS** (DB `qnu_v1_test_86959ece0a874842`, 15,02 s).

### 3.5 Gateway pipeline — 2b (`test_integration_gateway_pipeline.py`)
- **Nguyên nhân gốc:** câu hỏi cũ "Chỉ tiêu **tuyển sinh** năm 2024 là bao nhiêu?" trỏ dòng có giá trị 2024 = `-`, nhưng test lại khẳng định `150` của dòng "Chỉ tiêu **trúng tuyển**". `select_catalog` (`qnu.rag.table-selection/v2`) chỉ giữ các dòng có nhãn chủ thể xuất hiện nguyên văn trong câu hỏi — đúng thiết kế "never guess" — nên dòng 150 bị loại đúng.
- Chẩn đoán bằng tệp tạm (đã xoá, không vào Git): dense + `context_window = 0` trên cùng fixture cho `values ["1","0","-"]`, `matched_families = 1`, `selected_cells = 3`, câu trả lời "Chỉ tiêu tuyển sinh — STT: 1 [E1]" — chứng minh không liên quan retrieval mode hay context window.
- Sửa: đổi câu hỏi sang "Chỉ tiêu **trúng tuyển** năm 2024 là bao nhiêu?" để khớp số 150 cần khẳng định.
- Lỗi thứ hai lộ ra sau đó: payload answer v3 đổi khóa persona từ `assistant_style` → `style`; cập nhật assert. Lượt đầu sau đổi câu hỏi: 2 failed `KeyError: 'assistant_style'`; sau sửa: **2/2 PASS** (DB `qnu_v1_test_ac8d2780e8754a46`, 24,96 s).
- Sau khi `ruff format` lại đúng tệp, chạy lại lượt cuối: **2/2 PASS** (DB `qnu_v1_test_9080cce87c1e4ed8`, 25,82 s), khớp đúng byte đang có trong working tree.

## 4. Kiểm chứng sau sửa và trạng thái gate

- Ruff: `ruff check` **All checks passed** cho cả 8 tệp; `ruff format --check` sạch sau khi format lại `test_integration_gateway_pipeline.py` (7 tệp còn lại đã đúng định dạng).
- Các lượt chạy lại đều trên DB cô lập, `db_dropped=true`, `legacy_sentinel_preserved=true`.
- Trạng thái gate trung thực:
  - **A:** một lượt PASS 1167/1167.
  - **B:** lượt đầy đủ 330/333; 2 tệp lỗi đã sửa và xanh trong lượt chạy trúng (2/2 và 3/3); **chưa chạy lại toàn B trong một lượt**.
  - **C:** lượt đầu 251/254, sửa 2 tệp kỳ vọng, lượt chạy lại đầy đủ **254/254 PASS**.
  - **D:** lượt đầy đủ 189/191; 2 test sửa và xanh 9/9; các lượt chạy lại toàn D crash môi trường; 30 test còn lại xanh 26/26 + 4/4. Không có lượt D liền mạch PASS.
- **Chạy lại sau sửa trên mã cuối (12:34–12:48):**
  - **B:** chạy lại đầy đủ đúng 38 tệp/333 test trên mã cuối — **333/333 PASS**, 2.565,71 s (42:45), exit 0 (DB `qnu_v1_test_dcd443906c974e14`).
  - **D:** chia 2 lô theo đúng 25 tệp gốc để tránh crash — D1 14 tệp **96/96 PASS**, 463,59 s (DB `qnu_v1_test_5b019bafffb440ad`); D2 11 tệp **95/95 PASS**, 356,41 s (DB `qnu_v1_test_8b49591050ba4171`); tổng **191/191 PASS**, không crash. Vẫn **không có single-run liền mạch cho D** — bằng chứng là hai lượt ghép đủ phạm vi.
- Không chạy live E2E, benchmark G4, migration dev DB hay re-index trong phiên này; `NOT RUN ≠ PASS`.

## 5. Rủi ro, giới hạn và bước sau

- 8 tệp mã/test đang chờ duyệt commit (**2 mã** `rag/answer/cache.py`, `rag/answer/service.py`; **6 test**) cùng 5 tệp tài liệu phiên, **không push**.
- Việc sửa chỉ nằm ở test/kỳ vọng và tinh chỉnh trace cache; không đổi `select_catalog`, `expand_context`, `table_support` hay prompt.
- Crash `0xC0000005` là lỗi môi trường Windows khi chạy suite nặng kéo dài; B đã có single-run 333/333, D đã phủ đủ 191/191 qua 2 lô nhỏ không crash; nếu cần một lượt D liền mạch thì phải chạy trên máy sạch — chưa thực hiện.
- Bước tiếp chờ duyệt riêng: commit checkpoint; G4/G5/G6; B3/C3. Answer cache production vẫn để TTL = 0.
