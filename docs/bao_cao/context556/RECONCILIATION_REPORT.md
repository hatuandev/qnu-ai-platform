# Context556 — Đối chiếu canonical source

**RECONCILIATION_BLOCKED.** Chọn trường hợp C+D: cấu trúc/ID thay đổi và canonical cũ thiếu nội dung. Có 11 assertion map chính xác; A12 bị chặn riêng. Không tạo proposal 11 mục thay cho inventory12 và không tạo import-package hợp lệ khi thiếu bằng chứng.

Đích xác minh là `bnd_21c09bbc6ca0 / ks_rev_84c4950c9ce2`, cùng DOCX nhưng khác MD/JSON; không có revision exact-match khác trong inventory của binding đã audit. Base projection tươi chỉ dùng phân tích; stored artifact còn replay mismatch nên chưa đủ điều kiện nhập thật.

## Đủ 12 quan hệ, giữ nguồn/đích/phạm vi/điều kiện/ngoại lệ

| Quan hệ | Unit trước → sau | Nội dung | Giới hạn/điều kiện | Kết quả |
|---|---|---|---|---|
| A01 | qnu:l006 → qnu:l006 | Đơn vị SV/% và 12 chương trình | Toàn Bảng1; không mở rộng điều kiện riêng | MAPPED |
| A02 | qnu:l006 → qnu:l006 | 2027 là dự kiến, chưa nghiệm thu | c10–c12; không suy thành kết quả thực tế | MAPPED |
| A03 | qnu:l006 → qnu:l006 | Hồ sơ thiết bị nhóm A/kế hoạch2027 | Workflow r001–r006, không c10/c11/c12; đủ lịch kiểm định + quyết định mới được gia hạn ≤15 ngày làm việc; loại nhómB/2025/ghi nhận2026/ngân sách | MAPPED |
| A04 | qnu:l006 → qnu:l006 | Đối chiếu thực hành AM-0007 | Chỉ r003; loại AM-0070 | MAPPED |
| A05 | qnu:l006 → qnu:l006 | Ngoại lệ hồ sơ thực tập nhóm B | r007–r012; đủ các điều kiện Phụ lụcII; tối đa30 ngày rồi cần bổ sung; không nhómA/miễn an toàn | MAPPED |
| A06 | qnu:p049 → qnu:p083 | Dữ liệu 2025, chốt31/12/2025 | Chỉ c04–c06 | MAPPED |
| A07 | qnu:p049 → qnu:p083 | Dữ liệu 2026, chốt tạm30/09/2026 | Chỉ c07–c09 | MAPPED |
| A08 | qnu:p049 → qnu:p083 | Dự kiến2027 lập18/10/2026 | Chỉ c10–c12; năm dữ liệu khác năm lập | MAPPED |
| A09 | qnu:p049 → qnu:p083 | Cách tính tỷ lệ cùng năm/làm tròn1 số | Toàn Bảng1; không thay unknown thành0 | MAPPED |
| A10 | qnu:p050 → qnu:p084 | Sổ xác nhận phòng máy AM-0007 | Chỉ r003, không AM-0070 | MAPPED |
| A11 | qnu:p051 → qnu:p085 | Ước tính2027 chưa nghiệm thu | Chỉ c11; không Ghi nhận2025/2026 | MAPPED |
| A12 | qnu:docx_footnote_2 → THIẾU | Giữ số0 đầu và mã dạng chuỗi | c02/r001–r003; thiếu canonical footnote2 nên không chuyển | BLOCKED |

`MAPPED` là đủ chứng minh mapping nguồn, **không phải đã duyệt**, không tự xác nhận điều kiện nghiệp vụ đã xảy ra. A03 `context_kind=workflow`, column_ids rỗng; không tạo fact hoặc dependency cho chỉ tiêu/tỷ lệ sinh viên. Nội dung điều kiện, reason, scope, quote và offsets/text hash của mọi assertion map được giữ nguyên và đã kiểm tra bằng assertion trong bước xuất báo cáo.

A12 còn nhắm c02: header cột này của bản cũ bị lặp label do ô gộp, khác exact role metadata offline. Thiếu footnote là blocker gặp trước; không được mặc định c02 đã vượt kiểm tra role. Revision mới phải vượt cả hai kiểm tra.

## Sáu reference và vai trò

| Issue | Quan hệ theo vai trò đã có ở555 | Mapping sang canonical |
|---|---|---|
| O03 | direct: A03, A05; protective: A04, A10, A12, A06, A07, A08; conditional: A02, A11, A09 | BLOCKED — RECONCILIATION_REFERENCE_TARGET_BLOCKED |
| O04 | direct: A05; protective: A06, A07, A08; conditional: A02, A11 | MAPPED — evidence/đích đã map |
| O05 | direct: A03, A05; protective: A04, A10, A12, A06, A07, A08; conditional: A02, A11, A09 | BLOCKED — RECONCILIATION_REFERENCE_TARGET_BLOCKED |
| O06 | direct: A03, A05 | MAPPED — evidence/đích đã map |
| O07 | direct: A05 | MAPPED — evidence/đích đã map |
| O08 | protective: A04, A10, A12 | BLOCKED — RECONCILIATION_UNIQUE_STRUCTURAL_SOURCE_REQUIRED |

O03/O05 có body chính xác (Điều15/đoạn quy trình và phụ lục), nhưng tập đích chứa A12 chưa map được nên assessment toàn phần bị chặn. Không có nghĩa chúng thiếu toàn bộ body hoặc chặn mọi quan hệ Bảng1. O08 trực tiếp cần footnote2 bị thiếu. O04/O06/O07 map được. Reference assessments vẫn là thông tin để người dùng duyệt, không tự thành effective graph edges.

## Hash và trạng thái

- Original552: `80308912eba6ceecfcec7283e7ebedef225fe756000eb57c14602b0b58bbcfc3`.
- Revised553: `33d9cdae6fc80547aa6243ea7ac11d94b9fa5e9b765398ba569a9905870f3fc2`.
- Revised555: `0ae13c8d1b3584506a4aad171cf5464a19e8dcf2c06767e47e93ca0df9ac6840`; vẫn gắn `offline544/draft544`.
- **New canonical proposal hash: KHÔNG CÓ**, vì A12 thiếu; không sửa hash/binding/checkpoint cũ để giả khớp.
- Offline555 giữ đủ12assertion/18issue O01–O08/S01–S10. Không đóng/gộp issue, không chuyển approval. Revision thật hiện không có pending proposal semantic; **0 issue được stage mới bởi556**.
- Kiểm chứng checksum trước/sau giữ 14 file552 +5file553 +5file555 cùng manifest. Full mapping sanitized ở [assertion-binding-map.json](assertion-binding-map.json).
