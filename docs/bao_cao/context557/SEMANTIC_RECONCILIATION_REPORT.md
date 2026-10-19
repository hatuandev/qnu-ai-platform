# Context557 — Đủ 12/12 quan hệ

**RECONCILIATION_PASS**, sau đó **STAGED — WAITING_FOR_REVIEW**. Source thật `bnd_21c09bbc6ca0`, revision `ks_rev_2b5e0352565f`. Không còn blocker thiếu footnote hoặc sai role c02 của Context556; source hiện tại giữ header đúng và đủ native footnote.

| Quan hệ | Evidence unit cũ → mới | Ý nghĩa | Target/phạm vi/điều kiện/ngoại lệ | Binding |
|---|---|---|---|---|
| A01 | `qnu:l006` → `qnu:l006` | SV và % | Toàn Bảng1; điều kiện riêng không lan toàn bảng | PASS |
| A02 | `qnu:l006` → `qnu:l006` | 2027 là dự kiến | Chỉ c10–c12, chưa phải nghiệm thu | PASS |
| A03 | `qnu:l006` → `qnu:l006` | Hồ sơ thiết bị nhóm A/2027 | Workflow r001–r006; không c10–c12. Cần lịch kiểm định trùng mốc và quyết định; tối đa15ngày làm việc; loại nhóm B/2025/ghi nhận2026/ngân sách | PASS |
| A04 | `qnu:l006` → `qnu:l006` | Chứng cứ AM-0007 | Chỉ r003, không AM-0070 | PASS |
| A05 | `qnu:l006` → `qnu:l006` | Ngoại lệ hồ sơ thực tập nhóm B | r007–r012, đủ điều kiện Phụ lụcII; tối đa30ngày, không nhóm A/miễn an toàn | PASS |
| A06 | `qnu:p049` → `qnu:p049` | Chốt2025:31/12/2025 | c04–c06 | PASS |
| A07 | `qnu:p049` → `qnu:p049` | Chốt tạm2026:30/09/2026 | c07–c09 | PASS |
| A08 | `qnu:p049` → `qnu:p049` | Dự kiến2027 lập18/10/2026 | c10–c12, không suy năm lập thành năm dữ liệu | PASS |
| A09 | `qnu:p049` → `qnu:p049` | Tỷ lệ cùng năm, làm tròn1số | Toàn Bảng1, không thay unknown bằng0 | PASS |
| A10 | `qnu:p050` → `qnu:p050` | Sổ phòng máy AM-0007 | Chỉ r003, không AM-0070 | PASS |
| A11 | `qnu:p051` → `qnu:p051` | Ước tính2027 chưa nghiệm thu | Chỉ c11, không Ghi nhận2025/2026 | PASS |
| A12 | `qnu:docx_footnote_2` → `qnu:docx_footnote_2` | Footnote giữ mã có số 0 đầu | c02/r001–r003:0012,00027,AM-0007 dạng chuỗi | PASS |

Source unit IDs khớp vì hai bên dùng native builder hiện tại, nhưng không dựa vào việc trùng ID để chấp nhận. Công cụ đã xác minh body nguyên văn, locator, ancestry/role, bảng raw/state grid và exact role từng cột đích. Dựng mới evidence identity theo đúng source/revision/hash, kiểm từng span/codepoint; 83 binding trong proposal lưu thật đã được kiểm độc lập.

Mọi evidence quote, scope, điều kiện, ngoại lệ, reason và context_kind giữ nguyên. Mapping JSON chứa cả evidence/target cũ-mới, offsets/text hash/source identity và issue IDs lịch sử. Quote plaintext/corpus không được đưa vào gói báo cáo. A03 vẫn `workflow`, columns rỗng, không vào fact SV; A12 là footnote XML thật, không thay bằng paragraph gần giống.

## Sáu reference và 18 issue

| Issue | Vai trò trên quan hệ | Đối soát |
|---|---|---|
| O03 | direct: A03, A05; protective: A04, A10, A12, A06, A07, A08; conditional: A02, A11, A09 | PASS |
| O04 | direct: A05; protective: A06, A07, A08; conditional: A02, A11 | PASS |
| O05 | direct: A03, A05; protective: A04, A10, A12, A06, A07, A08; conditional: A02, A11, A09 | PASS |
| O06 | direct: A03, A05 | PASS |
| O07 | direct: A05 | PASS |
| O08 | protective: A04, A10, A12 | PASS |

O03/O05 nay map được cả đích A12; O08 có lại footnote 2. O05 giữ 2 direct /6 protective /3 conditional, không biến thành12 điều kiện trực tiếp. Cả18 issue O01–O08/S01–S10 được map sang ID mới khi contract yêu cầu, giữ labels và câu hỏi. Không tự đóng/gộp issue hoặc chuyển quyết định cũ. Reference assessments chưa thành effective graph edges.

## Ba hash khác nhau cần phân biệt

- Revised555 lịch sử: `0ae13c8d1b3584506a4aad171cf5464a19e8dcf2c06767e47e93ca0df9ac6840`.
- Gói canonical557 chuẩn bị: `e98ea06fc7a31450005a45384c4ac789d334afd5262573bd13e4ac4dcf814d2c`.
- **Proposal pending đang lưu để người dùng duyệt:** `543ddd61aa0b1527babe8c6adcb122c5cb2157f30d542c91d1de6fa5407207df`.
- Input hash: `343aad542852738ee5d1e39c28b133d42975b68ca433c99a7b48bc4fa5be1cad`.

Importer chính thức tạo envelope với metadata/audit và thời điểm `at` mới, đều tham gia proposal hash. Vì vậy hash gói chuẩn bị và hash pending thật khác nhau đúng contract; không đổi hash cũ để giả khớp. Người dùng phải duyệt hash pending đang lưu. Đã kiểm full payload hash thực tế và binding, không bỏ guard/timestamp khỏi kiểm tra integrity.

POST import200 duy nhất một lần; session mới và rebuild đọc lại đúng pending. Chưa human approval, semantic_effective, snapshot active hoặc publication. Những cảnh báo nguồn ngoài18 issue ngữ nghĩa vẫn cần đối soát riêng.

[Mapping đầy đủ](semantic-binding-map.json), [receipt thực](staging-receipt.json), [checksum](source-checksums.json).
