# Sẵn sàng đối chiếu ngữ nghĩa — Context555

**Chưa duyệt, chưa áp dụng, chưa xuất bản.** Bản sửa đã tách A03 khỏi các ô sinh viên và phân loại tham chiếu. Việc gắn gói offline vào ứng dụng thật đang **BLOCKED do hash nguồn khác nhau**; không phải một proposal đã có trong màn hình ứng dụng.

## Gói nào đang được xem

| Mốc | Proposal hash |
|---|---|
| Context552 gốc | `80308912eba6ceecfcec7283e7ebedef225fe756000eb57c14602b0b58bbcfc3` |
| Context553 trước sửa A03 | `33d9cdae6fc80547aa6243ea7ac11d94b9fa5e9b765398ba569a9905870f3fc2` |
| Context555 mới | `0ae13c8d1b3584506a4aad171cf5464a19e8dcf2c06767e47e93ca0df9ac6840` |
| Input hash offline | `0cced34a5a3b7b356bd4ce63df80e49749ec41e3686860b27809c8ed2549dcd9` |

Nguồn offline vẫn là `offline544/draft544`. Hai checkpoint 552/553 giữ nguyên tất cả file đã seal. Gói mới tại [import-package.json](../../../backend/storage/context555-review-ready/import-package.json), cùng [proposal](../../../backend/storage/context555-review-ready/proposal.json), [receipt](../../../backend/storage/context555-review-ready/checkpoint.json) và [manifest](../../../backend/storage/context555-review-ready/manifest.json). Các tệp này nằm trong Storage local, không được commit hoặc đưa corpus vào ZIP báo cáo.

## 12 quan hệ hiện tại

Mọi target thuộc bảng t001. “Đủ văn bản để trình đối chiếu” chưa xác nhận điều kiện của một hồ sơ thực tế đã thỏa.

| Quan hệ | Nguồn | Đối tượng/phạm vi và điều kiện cần giữ | Mục chờ quyết định |
|---|---|---|---|
| A01 | l006 [0,132) | Chú thích đơn vị toàn bảng: lượng người học là SV, tỷ lệ là %. Không biến mã/tên thành số lượng. | S01 |
| A02 | l006 [132,217) | c10/c11/c12 năm 2027 là phương án dự kiến, chưa nghiệm thu; không mở sang 2025/2026. | S02 |
| **A03** | l006 [218,520) + toàn l014 | **Ngữ cảnh hồ sơ thiết bị nhóm A, kế hoạch 2027; không trực tiếp sửa c10/c11/c12.** r001–r006 là tập chủ thể, không phải danh sách hồ sơ đã được gia hạn. Cần lịch kiểm định trùng khóa dự kiến, văn bản thông báo và quyết định Phòng Đào tạo. Tối đa 15 ngày làm việc từ hạn xác nhận ban đầu; loại B, dữ liệu 2025/ghi nhận 2026, chỉ tiêu và ngân sách. | **S03 mới**, O05/O06 và O03 qua body |
| A04 | l006 [521,648) | Chứng cứ thực hành riêng r003/AM-0007, không áp r004/AM-0070. | S04 |
| A05 | l006 [648,743) + l015/l012 khoản 3/p090/p092 | Hồ sơ thực tập sáu chương trình B (r007–r012), chỉ khi nơi thực tập đóng cửa làm chậm chữ ký, có nhật ký/xác nhận cùng kỳ và biên bản xác minh trực tuyến theo nguồn. Tạm thay chữ ký tối đa 30 ngày từ hết thực tập; quá hạn chưa xác nhận thì cần bổ sung. Không áp A, không miễn an toàn. | S05; O03/O04/O05/O06/O07 |
| A06 | p049 [0,53) | c04–c06: dữ liệu 2025 chốt 31/12/2025. | S06 |
| A07 | p049 [53,83) | c07–c09: dữ liệu 2026 **tạm** chốt 30/09/2026. | S07 |
| A08 | p049 [83,119) | c10–c12: dự kiến 2027 lập 18/10/2026; ngày lập không biến năm dữ liệu thành 2026. | S08 |
| A09 | p049 [119,222) | Tỷ lệ từng dòng/dòng tổng lấy số lượng cùng năm, làm tròn một chữ số. Không áp làm tròn mã/số lượng và không tự dùng tỷ lệ Bảng 1 làm biến Q. | S09; O05 conditional, chưa có chứng cứ nối đầu vào Q |
| A10 | toàn p050 | Sổ xác nhận phòng máy của r003/AM-0007; loại AM-0070. Khác yêu cầu chứng cứ rộng hơn của A04. | **O01 dùng lại**, không thêm S11 |
| A11 | toàn p051 | c11 chỉ là ước tính lập kế hoạch, chưa nghiệm thu; không áp c05/c08 ghi nhận 2025/2026. A02/A08 giữ nghĩa chung của c10/c12. | **O02 dùng lại**, không thêm S12 |
| A12 | toàn footnote_2 | c02 tại r001/r002/r003, giữ nguyên `0012`, `00027`, `AM-0007` dạng chuỗi. | S10 và O08, hai câu hỏi riêng |

11 quan hệ ngoài A03 giữ nguyên payload Context553. AM-0070 vẫn thuộc tập chủ thể nhóm A của A03 nếu hồ sơ đáp ứng điều kiện; nó không nhận hai yêu cầu riêng của AM-0007 trong A04/A10.

## Sáu reference để người dùng quyết định

| Issue | Mapping cần xác nhận | Điều chưa được phép suy |
|---|---|---|
| O03 / heading Điều 15 | Chỉ container đến body l012/p084; các liên kết lấy bằng chứng từ body, có thể đọc cùng O04/O05. | Heading không tạo quy tắc mới hoặc chi phối mọi dữ liệu Bảng 1. |
| O04 / l012 | Khoản 3 direct A05; khoản 2 protective A06/A07/A08; khoản 1 chỉ conditional A02/A11 khi đúng quy trình Q. | SV/% không tự là biến A/B/C; 30 ngày thẩm định lại không thay mốc của hai ngoại lệ A/B. |
| O05 / p084 | Direct A03/A05; protective A04/A10/A12 và A06/A07/A08; conditional A02/A11/A09. Không còn liên kết độc lập A01. | Chưa chứng minh tỷ lệ Bảng 1 dùng trong Q. Chỉ xác nhận đúng giới hạn conditional, không xác nhận liên hệ đầu vào còn thiếu. |
| O06 / p090 | Direct A03 qua l014 và A05 qua l015; hai ngoại lệ độc lập. | Không hợp nhất ngoại lệ, không sửa mã hoặc quy đổi dữ liệu thiếu. |
| O07 / s036 | Direct chỉ A05, có l015/p092. | Không sinh quyền gia hạn thiết bị A03. |
| O08 / footnote_2 | Bảo vệ định danh A04/A10/A12. | Không đóng S10 hoặc O01 chỉ vì cùng đọc footnote. |

Tất cả **8 O + 10 S = 18 issue vẫn chờ quyết định**. Đủ nội dung nguồn để trình bày quy tắc không đồng nghĩa đã có human approval. Không issue nào tự resolved vì đọc được nguồn hoặc sửa proposal.

Có thể đọc chung O01/A10 với S04; O02/A11 với S02/S08; O08 với S10; O03/O04/O05 cùng Điều 15; S03/O06 và S05/O07 theo ngoại lệ A/B. Mỗi ID vẫn cần quyết định hợp lệ riêng. Không dùng một ghi chú chung để giải quyết cả nhóm.

## Vì sao chưa đưa vào ứng dụng thật

Audit chỉ đọc phát hiện revision `ks_rev_84c4950c9ce2` của source `bnd_21c09bbc6ca0`, trạng thái review_required, có cùng hash DOCX gốc. Tuy nhiên:

| Cặp nguồn | Offline | Revision đang có |
|---|---|---|
| Markdown SHA256 | `cf52345162c89e025def74b988d1b3e2bb160e761776365cf113d40573ed2d7c` | `491a022b54ecfd4ed3166bbd42eaba5c7c9e41bc26d419e405833f60c242e1c6` |
| Structured SHA256 | `d687fe7c4950ec44663cb84e11eb4e5e20ba4b62586422fdcb3bab03d49c147f` | `b9b00f1915988c79493a340ce5d37a6306900192dfc0cd22d93c8c8e072de41c` |

Không có cặp revision khớp, nên chưa liên kết source/revision thật với proposal mới. Cùng tên hoặc cùng file gốc không đủ để chuyển bằng chứng. Không sửa hash, giả revision hoặc ghi DB thủ công.

**Bước cần người dùng thực hiện:** chọn/xác định revision đúng cặp nguồn qua luồng nguồn của ứng dụng. Nếu chủ đích là dùng revision đang có với cặp khác, cần một lượt đối soát riêng trên chính canonical source đó, lập proposal/hash mới; không nhập cưỡng bức gói này và không tái sử dụng quyết định/hash offline.

## Cách duyệt khi đã có revision hợp lệ

1. Mở Kho tri thức → bộ sưu tập chứa nguồn → chi tiết nguồn → chọn revision nháp đúng → Kiểm duyệt nguồn. Dùng bản mã đã được nạp ở môi trường được phép.
2. Chọn “Nhập đề xuất từ checkpoint đã đối soát”, tải `import-package.json`, ghi căn cứ chọn nguồn và tạo pending. Backend sẽ từ chối cặp không khớp.
3. Sau nhập, kiểm lại **revision và proposal hash mới trên ứng dụng**. Hash này khác hash offline vì có binding/audit staging theo revision thật. Không gửi quyết định theo hash offline.
4. Đọc từng assertion, đầy đủ điều kiện và loại trừ. Chọn từng scope issue và xác nhận reference liên quan bằng action riêng. Mục cần sửa thì yêu cầu sửa/từ chối; sửa target/scope phải tạo gói/hash mới và đối chiếu lại quyết định.
5. Chỉ khi đủ mọi issue và đủ quyền mới dùng hành động áp dụng đề xuất. Áp dụng vào nháp là một bước riêng với duyệt/xuất bản nguồn. Báo cáo này không đề nghị tự xuất bản dữ liệu.

Nếu vẫn ở revision có hash khác trong bảng trên, **dừng ở bước chọn revision**, không bấm nhập nhiều lần để thử vượt kiểm tra.

## Kết luận về trạng thái

Kết quả kiểm chứng triển khai và các giới hạn nằm trong [VALIDATION_REPORT](VALIDATION_REPORT.md). Không có quyết định người dùng thật, không annotation nào được áp vào nguồn thật. Không được gọi trạng thái này là E2E PASS. Việc tạo pending thật còn bị chặn bởi identity nguồn như mô tả trên.
