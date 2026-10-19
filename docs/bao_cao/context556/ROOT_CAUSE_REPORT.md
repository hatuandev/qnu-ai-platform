# Context556 — Nguyên nhân khác artifact

**ROOT_CAUSE_CONFIRMED.** Cùng bytes DOCX, nhưng revision đang lưu được tạo bằng nhánh xử lý cũ; khác biệt có thay đổi nội dung và cấu trúc, không chỉ serialization.

## Bằng chứng nguồn và thời điểm

- DOCX SHA256 `58b3f7806529e4e506a6e2569a83ac688b8468fba955d0fe6638444a02099274`, 102,423 byte. GET snapshot từ Storage và file DOCX local khớp từng byte; không suy từ tên file.
- Đích đã xác minh: `col_admissions / bnd_21c09bbc6ca0 / ks_rev_84c4950c9ce2`, trạng thái `review_required`, tạo lúc `2026-10-18 14:55:59.911591+00:00` (21:55:59 +07).
- Revision ghi normalizer `layout-v16-qnu-evidence`, profile `fe6d3468cf5c74d8ec2a95b40f2e05338c37a4202f8fad692d2b64a9cf9b468a`. Code hiện tại ghi `layout-v18-semantic-evidence`. Checkpoint offline không ghi đủ fingerprint dependency/parser để khẳng định chính xác toàn môi trường tạo nó.
- Chỉ đọc DB chung trong transaction READ ONLY và GET Storage. Không ghi/cập nhật revision.

## Diff theo tầng

| Thành phần | Offline552 | Canonical đang lưu | Phân loại và tác động |
|---|---|---|---|
| DOCX | Cùng SHA256/102.423 byte | Khớp từng byte | Nguồn gốc giống nhau |
| Markdown SHA256 | `cf52345162c89e025def74b988d1b3e2bb160e761776365cf113d40573ed2d7c` | `491a022b54ecfd4ed3166bbd42eaba5c7c9e41bc26d419e405833f60c242e1c6` | Metadata, cấu trúc và nội dung khác |
| JSON SHA256 | `d687fe7c4950ec44663cb84e11eb4e5e20ba4b62586422fdcb3bab03d49c147f` | `b9b00f1915988c79493a340ce5d37a6306900192dfc0cd22d93c8c8e072de41c` | Cấu trúc/evidence khác; không thể đổi hash |
| Block | 233 | 299 | Chỉ là chỉ số phụ; đối chiếu từng block ở JSON đính kèm |
| Footnote DOCX | 3 native footnote | Không có cả 3 | Footnote2 thiếu cả nguyên văn, chặn A12 |
| Đoạn từ ô bảng | Được lọc khỏi luồng prose | Rich-cell children bị materialize thêm | Dịch số thứ tự pNNN, gây cùng ID khác nghĩa |
| Bảng1 | Raw/state grid | Khớp toàn ma trận | Không mất raw cell trong Bảng1; 3 header đầu bị lặp tên do ô gộp |
| c04–c12 | Header/role gốc | Khớp nguyên trạng | Cho phép xác minh các đích số liệu này riêng |
| Page evidence | Alignment mới theo native units/brackets | token_match_on_aligned_preview | Locator DOCX dùng để đối chiếu; không lấy page cũ lấp unknown |
| Source inventory/raw evidence | Có | Thiếu | Metadata/provenance khác |
| Title/document/revision | Offline identity và title từ tên file | Identity/title của nguồn trong app | Khác metadata cũng làm hash khác ngay cả khi core khớp |

Markdown hai phía đều UTF-8 không BOM, LF, NFC; khác biệt không biến mất bằng đổi newline/Unicode. Trường frontmatter thay đổi: document_id, metadata, revision_id, title. Chỉ số byte/whitespace/control được ghi trong [source-artifact-comparison.json](source-artifact-comparison.json); không chuẩn hóa rồi nhận là cùng artifact.

## Điểm bắt đầu khác và kiểm chứng nhân quả

Điểm phát sinh nằm ở builder DOCX: bản cũ đưa paragraph của rich table cell vào prose và không tích hợp native footnote evidence. Chạy cùng DOCX bằng historical builder lấy từ Git reference `2cde271f` tái tạo **đúng toàn bộ 299 core records theo thứ tự** (ID/type/body/parent/section) của revision lưu. Builder hiện tại cùng native evidence tái tạo **đúng 233 core records** offline. Kiểm tra này PASS; không chỉ so số lượng node. Đây là bằng chứng về thuật toán gây khác; không đủ để khẳng định Git commit/dependency deployment chính xác của tiến trình cũ.

Ví dụ bắt buộc: `p049 → p083`, `p050 → p084`, `p051 → p085`, `p084 → p145`, `p090 → p155`, `p092 → p161`. `l006/l014/l015/l012` và headings `s030/s036` giữ ID. **p084 của canonical là ghi chú AM-0007, không còn là đoạn quy trình đánh giá p084 offline**. Offset chỉ tái dùng sau khi toàn unit body khớp từng codepoint; binding/evidence ID/input hash được dựng mới.

## Blocker độc lập ở derived projection

Cặp MD/JSON đang lưu vượt kiểm tra pair/hash/revision. Tuy nhiên `proposal_base` từ artifact đang lưu trả `SEMANTIC_SNAPSHOT_INVALID / enrichment_structure`: manifest có **29 phần tử khác** với replay bằng code hiện tại, gồm context_refs mới. [structured-diff-summary.json](structured-diff-summary.json) giữ diff field-level. Fresh projection trong audit chỉ ở bộ nhớ, không đại diện cho việc cập nhật revision thật. Không bỏ guard này.

## Determinism và hướng khắc phục

Hai tiến trình Python, hai LocalStorage test độc lập, cùng runtime dependencies/bytes/config/identity cho MD/JSON/IDs/manifest/span/resource checksum giống nhau. PDF preview được tắt giống nhau ở cả hai; không chứng nhận toàn pipeline LibreOffice/PDF preview. Identity/title/revision khác vẫn hợp lệ làm artifact hash khác. Không cần nâng standard v1.0 hoặc vá parser hiện tại vì core hiện tại đã giữ đủ footnote.

Không sửa nguồn cũ để ép import. Cần một **revision nháp mới qua luồng chuẩn, được người dùng cho phép**, dùng pipeline hiện tại và kiểm chứng footnote2 + projection trước khi tạo proposal mới. Xem [REVIEW_READY.md](REVIEW_READY.md).
