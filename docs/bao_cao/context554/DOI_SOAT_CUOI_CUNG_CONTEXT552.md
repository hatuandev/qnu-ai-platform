# Đối soát cuối cùng Context552 sau khi tách 12 quan hệ

Ngày đối soát: **19/10/2026 — Asia/Bangkok**. Báo cáo phục vụ người dùng quyết định từng mục. **Chưa có quyết định duyệt nào được ghi nhận.**

## 1. Kết quả cần biết trước

Checkpoint hiện có **12 quan hệ, 18 mục đang mở: 8 issue gốc và 10 xác nhận phạm vi mới**. Không có 18 lỗi nội dung độc lập. Hai câu hỏi kiểm tra khác nhau có thể cùng dùng một đoạn nguồn hoặc cùng nói về một dòng.

Qua đọc lại source, proposal và mã xử lý hiện tại:

- Đủ nội dung nguồn để đọc cả 12 quan hệ và sáu deferred reference. Điều 15, các mục con, Phụ lục II.1/II.2 và footnote đều đã có trong context. Không còn tình trạng chỉ có heading đối với hai reference s030/s036.
- **11 quan hệ có đủ căn cứ để trình đối chiếu quy tắc**, với điều kiện diễn giải ghi ở bảng dưới. **A03 cần làm rõ đích gắn**: quy định gia hạn hồ sơ thiết bị không chứng minh rằng ba cột số liệu sinh viên c10/c11/c12 là đối tượng được gia hạn. Chưa khuyến nghị xác nhận nguyên phạm vi S03 hiện tại.
- Liên kết của O05/p084 với **toàn bộ 12 quan hệ** trong checkpoint cũ quá rộng nếu hiểu là 12 ràng buộc trực tiếp. Cần phân biệt quy định trực tiếp, bảo vệ định danh/thời gian và điều kiện chỉ phát sinh khi dùng dữ liệu trong đánh giá.
- **Không có issue nào đã được thay thế hoặc đóng chính thức.** Dữ liệu `reconciliation.reprocessed` đang rỗng. O01/O02 được dùng lại cho A10/A11, nên không có xác nhận mới thứ 11/thứ 12.
- Sáu reference chỉ chi phối những quan hệ nêu trong báo cáo. Mã hiện tại vẫn áp dụng proposal theo một lần duyệt trọn gói, nên một issue mở làm cả proposal chưa áp dụng được. Đây là cách kiểm soát giao dịch, không có nghĩa reference đó có hiệu lực trên mọi ô của Bảng 1.

Nhận định trước rằng “đã đủ nguồn để duyệt” cần hiểu hẹp hơn: **đủ văn bản nguồn không đồng nghĩa mọi liên kết đến đích đã được chứng minh**. Báo cáo này bổ sung và điều chỉnh phân loại; không sửa proposal để nhận là đã hết vấn đề.

## 2. Danh tính và cách đọc nhãn

| Thành phần | Giá trị đã kiểm lại |
|---|---|
| Nguồn/revision | `offline544` / `draft544` |
| Hash proposal gốc Context552 | `80308912eba6ceecfcec7283e7ebedef225fe756000eb57c14602b0b58bbcfc3` |
| Hash proposal 12 quan hệ đang đối soát | `33d9cdae6fc80547aa6243ea7ac11d94b9fa5e9b765398ba569a9905870f3fc2` |
| Input hash | `0cced34a5a3b7b356bd4ce63df80e49749ec41e3686860b27809c8ed2549dcd9` |
| Kiểm toàn vẹn | 14 tệp của checkpoint gốc và 5 tệp của revised checkpoint khớp manifest |
| Trạng thái | Offline, `WAITING_FOR_REVIEW`; chưa có pending revision trong UI ứng dụng thật |

**A01–A12** là nhãn đọc cho 12 quan hệ theo đúng thứ tự `annotations.notes`. **O01–O08** là tám issue gốc; **S01–S10** là mười xác nhận mới theo thứ tự trong checkpoint. Đây là nhãn của báo cáo, không phải issue ID mới. ID thật có trong phụ lục và [bảng ánh xạ JSON](issue-relation-map.json).

“Đủ căn cứ trình duyệt” nghĩa là có thể đọc nguồn, đích và điều kiện để ra quyết định. Nó chưa phải approval, chưa xác nhận một hồ sơ thực tế thỏa điều kiện và chưa cho phép publish.

## 3. Mười hai quan hệ sau khi tách

Mọi đích bên dưới thuộc `qnu:t001`. Tập “toàn bảng” trong payload bao gồm 12 chương trình và dòng tổng r013; quy định đơn vị/tỷ lệ chỉ áp cho loại giá trị được câu nguồn mô tả. Không áp đơn vị SV cho mã chương trình.

| Quan hệ | Nguồn và span Unicode [start,end) | Đích/phạm vi hiện lưu | Nội dung, điều kiện và ngoại lệ cần giữ | Mục quyết định / nhận định |
|---|---|---|---|---|
| **A01** — đơn vị chung | `qnu:l006` [0,132) | `table`; không hạn chế dòng/cột | Bảng gồm 12 chương trình; lượng người học dùng SV, tỷ lệ dùng %. Mã và tên không trở thành đại lượng SV. | **S01**. Đủ căn cứ trình duyệt như chú thích ngữ cảnh toàn bảng. |
| **A02** — tình trạng năm 2027 | `qnu:l006` [132,217) | `column`: c10,c11,c12; mọi dòng | Các đại lượng năm 2027 là phương án dự kiến, chưa phải kết quả nghiệm thu năm 2027. Ba đại lượng vẫn khác nhau. Không mở sang 2025/2026. | **S02**. Đủ căn cứ; bổ trợ O02/A11, không thay O02. |
| **A03** — thiết bị nhóm A | `qnu:l006` [218,520), kèm **toàn** `qnu:l014` [0,438) | `column`: r001–r006 × c10,c11,c12 | Chỉ hồ sơ xác nhận thiết bị của nhóm A, kế hoạch 2027; tối đa **15 ngày làm việc từ hạn xác nhận ban đầu**. Phải có văn bản thông báo lịch kiểm định trùng đợt khóa dự kiến **và** quyết định gia hạn của Phòng Đào tạo. Không sửa chỉ tiêu, số người học 2025, số ghi nhận 2026, nhóm B, hồ sơ ngoài nhóm A hoặc quyết định sử dụng kinh phí. | **S03**. Đủ văn bản điều kiện nhưng **cần làm rõ đối tượng đích**, xem mục 7. Không đề nghị bấm xác nhận nguyên payload hiện tại. |
| **A04** — chứng cứ riêng AM-0007 | `qnu:l006` [521,648) | `row`: r003; không hạn chế cột | Yêu cầu đối chiếu chứng cứ thực hành riêng cho AM-0007. Nêu rõ không mở sang AM-0070. | **S04**. Đủ căn cứ. Cùng đối tượng với A10 nhưng nội dung không hoàn toàn trùng. |
| **A05** — thực tập nhóm B | `qnu:l006` [648,743), kèm `l015` [0,633), `l012` [533,711), `p090` [0,278), `p092` [0,246) | `group`: r007–r012; không hạn chế cột | Quy tắc hồ sơ thực tập có điều kiện. Cơ sở tiếp nhận tạm đóng làm chậm chữ ký; có nhật ký cá nhân, xác nhận giảng viên cùng kỳ; có biên bản trực tuyến của Phòng Hợp tác doanh nghiệp, lịch trao đổi và danh sách người xác nhận. Tạm thay chữ ký giấy tối đa **30 ngày từ cuối đợt thực tập**. Quá hạn mà chưa có xác nhận cuối cùng thì “Cần bổ sung hồ sơ”. Loại nhóm A; không miễn an toàn. | **S05**. Đủ căn cứ trình duyệt **quy tắc có điều kiện, ngữ cảnh hồ sơ**. Không xác nhận cả sáu chương trình thực tế đều đủ điều kiện và không đổi số liệu SV. |
| **A06** — mốc năm 2025 | `qnu:p049` [0,53) | `column`: c04,c05,c06; mọi dòng | Dữ liệu năm 2025 chốt 31/12/2025. Không áp mốc này cho năm khác. | **S06**. Đủ căn cứ. |
| **A07** — mốc năm 2026 | `qnu:p049` [53,83) | `column`: c07,c08,c09; mọi dòng | Dữ liệu năm 2026 **chốt tạm** 30/09/2026; giữ chữ “tạm”. | **S07**. Đủ căn cứ. |
| **A08** — mốc lập dự kiến 2027 | `qnu:p049` [83,119) | `column`: c10,c11,c12; mọi dòng | Dự kiến cho năm dữ liệu 2027 được lập ngày 18/10/2026. Ngày lập năm 2026 không biến dữ liệu thành năm 2026. | **S08**. Đủ căn cứ. A02 nói trạng thái, A08 bổ sung ngày lập. |
| **A09** — quy tắc tỷ lệ | `qnu:p049` [119,222) | `table`; không hạn chế dòng/cột | Tỷ lệ từng dòng và dòng tổng tính từ số lượng **cùng năm**, làm tròn một chữ số thập phân. Chỉ các đại lượng tỷ lệ c06,c09,c12 chịu quy tắc này. Không làm tròn mã hoặc mọi số lượng. | **S09**. Đủ căn cứ giữ **chú thích toàn bảng** nếu đọc đúng mệnh đề “tỷ lệ”. Nếu sau này xuất thành quy tắc tính có kiểu, phải chọn riêng các cột tỷ lệ; payload hiện chưa biểu diễn một công thức thực thi. |
| **A10** — sổ phòng máy AM-0007 | `qnu:p050` [0,177) | `row`: r003; không hạn chế cột | Chỉ AM-0007 phải kèm sổ xác nhận sử dụng phòng máy phân tích dữ liệu. Loại AM-0070 dù tên có yếu tố “dữ liệu”. | **O01 dùng lại**. Đủ căn cứ trình duyệt. |
| **A11** — nghĩa đại lượng “Ước tính” | `qnu:p051` [0,223) | `column`: **c11**; mọi dòng | Ước tính là dữ liệu lập kế hoạch, không phải kết quả nghiệm thu. Toàn câu nhắc ba cột 2027 nhưng chỉ định đại lượng “Ước tính”. Loại “Ghi nhận” 2025/2026 tại c05,c08. | **O02 dùng lại**. Đủ căn cứ; không mở sang c10/c12 bằng suy đoán. A02/A08 giữ phần ngữ cảnh chung của nhóm năm. |
| **A12** — mã có số 0 đầu | `qnu:docx_footnote_2` [0,121) | `column`: r001,r002,r003 × **c02** | `0012`, `00027`, `AM-0007` là chuỗi; mất số 0 làm đổi đối tượng. Không coi `0012` bằng `0120`, không ép mã sang số nguyên. | **S10**, tham chiếu **O08**. Đủ căn cứ; phạm vi gắn footnote giới hạn đúng ba mã được nêu, không xóa yêu cầu giữ mã chuỗi cho các mã còn lại. |

Tách từ bốn annotation gốc: annotation l006 → A01–A05; p049 → A06–A09; p050 → A10; p051 → A11. A12 là quan hệ được bổ sung từ footnote đã tồn tại trong nguồn, không phải nội dung LLM viết thêm.

## 4. Ánh xạ đầy đủ tám issue gốc → quan hệ → xác nhận mới

Trong bảng này, **trực tiếp** là có điều khoản nói rõ quan hệ; **bảo vệ** là ngăn sai mã/năm; **có điều kiện** là chỉ phát sinh khi dùng dữ liệu trong quy trình đánh giá. Một liên kết bảo vệ hoặc có điều kiện không tự trở thành điều kiện áp dụng cho mọi ô.

| Issue gốc | Quan hệ liên quan sau đối soát | Xác nhận mới liên quan | Trùng/thay thế và nhận định để quyết định |
|---|---|---|---|
| **O01 — p050** | **Trực tiếp A10**. A04 cùng r003 nhưng nói yêu cầu chứng cứ rộng hơn; A12 bảo vệ định danh. | **S04** bổ trợ nội dung; **S10** hỗ trợ giữ mã. A10 không có S mới. | O01 được dùng lại, không bị thay. S04 không thay yêu cầu sổ phòng máy; S10 không thay quyết định về dòng. Đủ căn cứ cho scope r003. |
| **O02 — p051** | **Trực tiếp A11**. **A02,A08** bổ sung trạng thái chung nhóm năm 2027 và ngày lập. | **S02,S08**. A11 không có S mới. | Cùng năm nhưng khác mức phạm vi/thuộc tính, không trùng hoàn toàn. Đủ căn cứ cho c11 khi giữ A02/A08 độc lập. |
| **O03 — s030, heading Điều 15** | Là **cửa vào nội dung O04/l012 và O05/p084**; không tự tạo một quy định từ heading. Quan hệ cụ thể theo hai hàng O04/O05, đặc biệt A05 và A03. | **S03,S05** trực tiếp qua body; các S về mã/năm ở O04/O05 chỉ có vai trò tương ứng. Không có S riêng thay O03. | Chồng lấp bằng chứng với O04/O05. Có thể trình cùng một nhóm đọc Điều15, nhưng chưa gộp hay xóa ID. Body đã đủ; cần thu hẹp liên kết advisory trước khi hiểu đây là xác nhận toàn Bảng1. |
| **O04 — l012** | Khoản 3 **trực tiếp A05**. Khoản 2 bảo vệ năm của **A06,A07,A08** khi chọn chứng cứ đánh giá. **A02,A11** chỉ liên quan khi kiểm việc dùng dự kiến làm kết quả quan sát. | **S05** trực tiếp; **S06,S07,S08** theo năm; **S02** và O02 theo điều kiện sử dụng. | O04 nằm trong body O03. Chưa có bằng chứng rằng tỷ lệ/SV Bảng1 chính là biến A,B,C của công thức Q. Đủ nguồn, nhưng không xác nhận một ánh xạ đầu vào Q chưa có. |
| **O05 — p084** | **Trực tiếp A03,A05** về giới hạn A/B. **Bảo vệ A04,A10,A12** về định danh; **A06,A07,A08** về mốc/năm. **A02,A11** khi phân biệt dự kiến với chứng cứ thực đo; **A09** chỉ nếu có sử dụng tỷ lệ trong đánh giá được chứng minh. **A01 chưa có quan hệ chi phối độc lập được chứng minh.** | **S03,S05** trực tiếp; **S04,S10,S06,S07,S08** bảo vệ; **S02,S09** có điều kiện. Không mặc định chặn S01. | Checkpoint hiện ghi liên kết cả A01–A12, cần thu hẹp/giải thích. Body đầy đủ nhưng chứng cứ cho “chi phối trực tiếp tất cả” chưa có. Không nên duyệt nguyên cách diễn giải rộng đó. |
| **O06 — p090, dẫn nhập Phụ lục II** | **A03** qua II.1/l014 và **A05** qua II.2/l015. Cấm dùng ngoại lệ để sửa mã hoặc quy đổi dữ liệu thiếu. | **S03,S05**. | Phần nhóm B chồng lấp O07; O06 còn giới hạn tách biệt hai ngoại lệ nên không bị O07 thay hoàn toàn. A05 đủ nguồn; phần A03 còn vướng đích cột như S03. |
| **O07 — s036, II.2** | **Trực tiếp chỉ A05**. Điều loại trừ nhóm A là ranh giới của ngoại lệ B, không tự tạo quyền gia hạn A03. | **S05**. | Body l015 được O06 dùng lại nhưng câu hỏi O07 là đầy đủ điều kiện B. Đủ nguồn để trình xác nhận tham chiếu này cho A05, không phải cho mọi quan hệ. |
| **O08 — footnote_2** | **Trực tiếp A12**; bảo vệ đúng định danh trong **A04,A10**. | **S10** trực tiếp, **S04** liên quan; O01 giữ câu hỏi dòng riêng. | Cùng evidence với A12/S10, có thể đọc và quyết định cạnh nhau. O08 hỏi quan hệ tham chiếu; S10 hỏi tập ba dòng/cột c02. Chưa có thay thế chính thức. |

**Không bắt buộc mọi S phải có một O “cha”.** S01 và S09 phát sinh vì tách các quy định vốn chưa có câu hỏi scope riêng; không được gán thêm một deferred reference chỉ để làm bảng ánh xạ kín.

## 5. Ánh xạ ngược đủ mười xác nhận mới

| Xác nhận mới | Quan hệ / nguồn | Issue gốc liên quan | Mức liên quan / đề nghị người dùng xem |
|---|---|---|---|
| **S01** | A01 / l006 | Không có O trực tiếp. O05 đã gắn A01 trong advisory cũ nhưng chưa chứng minh quan hệ riêng. | Xem đơn vị chung; không cần coi Điều15 là điều kiện cho việc nhận biết SV/%. |
| **S02** | A02 / l006 | O02 bổ trợ; O03/O04/O05 khi sử dụng dữ liệu đánh giá | Xác nhận ba cột 2027 là dự kiến; giữ khác biệt đại lượng. |
| **S03** | A03 / l006 + l014 | O05,O06 trực tiếp; O03 là nhóm cha theo body | **Yêu cầu làm rõ đích hồ sơ thiết bị trước**; không chấp thuận nguyên ba cột số liệu chỉ vì cùng năm. |
| **S04** | A04 / l006 | O01 cùng dòng; O05/O08 bảo vệ mã | Xác nhận r003 và giữ loại r004, phân biệt với yêu cầu sổ ở A10. |
| **S05** | A05 / l006 + l015/l012/p090/p092 | O03,O04,O05,O06,O07 | Xem cùng một nhóm ngoại lệ B; từng ID vẫn giữ câu hỏi và bằng chứng riêng. Duyệt quy tắc không xác nhận hồ sơ thực tế. |
| **S06** | A06 / p049 | O05 bảo vệ năm; O04/O03 khi dùng chứng cứ đánh giá | Chốt đúng c04–c06, không coi bảng số lượng là biến Q khi chưa có căn cứ. |
| **S07** | A07 / p049 | O03/O04/O05 theo năm/kỳ đánh giá | Chốt tạm đúng c07–c09. |
| **S08** | A08 / p049 | O02 bổ trợ; O03/O04/O05 theo năm/kỳ | Dữ liệu 2027, ngày lập 2026. |
| **S09** | A09 / p049 | Không có O bắt buộc trực tiếp; O05 khi tỷ lệ được dùng trong đánh giá có căn cứ | Xác nhận chú thích về tỷ lệ cùng năm, không làm tròn mọi ô. |
| **S10** | A12 / footnote_2 | O08 trực tiếp; O05/O01 bảo vệ định danh liên quan | Xác nhận c02 của r001–r003; có thể đọc cùng O08 nhưng không tự đóng O08. |

## 6. Sáu deferred reference: liên kết hiện lưu và phạm vi thực sự được chứng minh

| Reference | `reference_assessments` hiện lưu | Kết quả đối soát độc lập | Đủ hay thiếu gì? |
|---|---|---|---|
| **O03/s030** | A05,A02,A07,A08,A09; supporting l012 và p084 | Heading chỉ dẫn tới body; hiệu lực nằm ở từng khoản. l012.3 nói A05; p084 nói giới hạn A03/A05, mã và năm. Danh sách hiện lưu chưa thể hiện rõ phân cấp; A06 bị bỏ dù quy tắc không đổi năm không chỉ nói 2026/2027. | **Đủ body, cần làm rõ liên kết**. Không thiếu văn bản Điều15. Không dùng heading để xác nhận hiệu lực toàn bảng. |
| **O04/l012** | A05,A02,A07,A08 | Trực tiếp A05 theo khoản3. Khoản2 cấm đổi năm chứng cứ là bảo vệ chung khi chọn năm; A06 cũng thuộc trường hợp có thể liên quan. Điều kiện xếp loại Q không tự áp cho số SV hoặc tỷ lệ bất kỳ. | **Đủ source; thiếu bằng chứng nếu muốn khẳng định cột nào là biến A/B/C hoặc tự đổi tỷ lệ Bảng1 thành Q.** Không phải thiếu để duyệt quy tắc hồ sơ B. |
| **O05/p084** | **A01–A12** | Tách ba lớp như mục4: A03/A05 trực tiếp; mã và năm là bảo vệ; đánh giá định lượng là có điều kiện. Không chứng minh một mệnh đề mới chi phối A01 chỉ từ đoạn yêu cầu ghi đơn vị của các biến. | **Nguồn đủ, ánh xạ hiện quá rộng**. Cần thu hẹp hoặc ghi rõ điều kiện, chưa khuyến nghị duyệt nhãn “liên quan cả 12” như một ràng buộc trực tiếp. |
| **O06/p090** | A03,A05; supporting p090,l014,l015 | Hai ngoại lệ hồ sơ tách biệt; không cho sửa mã/unknown. | **Đủ body và điều kiện**. Cần giải quyết cách gắn đích A03; A05 có thể trình đối chiếu riêng. |
| **O07/s036** | A05; supporting l015,p092 | Chỉ ngoại lệ B, có đủ hồ sơ thay thế và thời hạn/hậu quả. | **Đủ căn cứ cho quan hệ A05**. Không cần xét lại A01–A12 để đọc mục này. |
| **O08/footnote_2** | A04,A10,A12; supporting footnote toàn văn | Giữ chuỗi mã, đồng thời bảo vệ nhận diện r003 khi áp A04/A10. | **Đủ căn cứ**; chồng lấp chứng cứ với S10 nhưng khác câu hỏi. |

### Reference đã được đọc không đồng nghĩa đã thành phụ thuộc ngữ nghĩa có hiệu lực

Checkpoint lưu hai loại liên kết khác nhau:

1. `related_evidence` của **A03** chứa l014; của **A05** chứa l015, khoản3 l012, p090, p092. Đây là các bằng chứng đi kèm được khai báo để đi theo quan hệ khi có quy trình áp dụng hợp lệ.
2. `reference_assessments` là phần phân tích để người dùng đọc. Ví dụ full p084 được lưu ở đây; không phải vì O05 liệt kê A01–A12 mà full p084 đã thành điều kiện của tất cả facts/chunks.

Do đó, việc người dùng đã đọc một reference không tự chứng minh mọi ràng buộc của nó đã được biểu diễn trong graph sau áp dụng. Cần kiểm đúng quan hệ phụ thuộc khi tiếp tục vòng đời thật. Lượt này không apply/rebuild để kiểm điều đó.

### Bằng chứng nào chưa có?

- **Thiếu chứng minh đích/role A03:** Bảng1 không có cột hồ sơ thiết bị. c10 là chỉ tiêu SV, c11 là ước tính SV, c12 là tỷ lệ. Giới hạn năm/nhóm đã rõ, nhưng chưa chứng minh quyền gia hạn hồ sơ gắn chính xác vào ba ô số liệu này. Có thể chọn biểu diễn như ngữ cảnh hồ sơ của nhóm A trong kỳ 2027 hoặc liên kết tới đối tượng hồ sơ đúng nguồn; muốn sửa phải tạo proposal mới/hash mới. Báo cáo không tự đổi payload.
- **Thiếu ánh xạ nếu tính đánh giá Q:** không có bằng chứng trong những quan hệ đang xét rằng chỉ tiêu SV, số lượng ghi nhận hay tỷ lệ ở Bảng1 chính là một trong các biến A/B/C của phép đánh giá. Không tự coi cùng là số hoặc phần trăm thì có thể thế vào Q.
- **Chưa có minh chứng hồ sơ cụ thể đủ điều kiện:** A03/A05 nêu quy tắc điều kiện. Chưa có văn bản gia hạn/nhật ký/biên bản thực tế của từng hồ sơ trong checkpoint này. Việc đó cần khi áp ngoại lệ cho hồ sơ, không ngăn người dùng xem xét quy tắc có điều kiện.

## 7. Các kiểm tra dễ nhầm

### AM-0007 và AM-0070

| Mã/raw | Row ID nguồn | Nhóm | Quan hệ riêng AM-0007 | Hệ quả cần giữ |
|---|---|---|---|---|
| `AM-0007` | `qnu:r003` | A | A04 và A10 | Có yêu cầu chứng cứ riêng và sổ phòng máy riêng. |
| `AM-0070` | `qnu:r004` | A | **Không nhận A04/A10** | Dù tên có “dữ liệu”, mã không tương đương AM-0007. |

Cả hai đều là thành viên nhóm A. Vì vậy AM-0070 vẫn có thể nằm trong đối tượng **quy tắc thiết bị nhóm A** nếu đúng hồ sơ và điều kiện năm 2027. Điều đó không làm AM-0070 nhận yêu cầu riêng của AM-0007. Việc chưa rõ đích cột A03 được giữ nguyên như nhận định ở trên.

A04 và A10 có phần nội dung gần nhau nhưng chưa nên xóa một trong hai: A04 là chứng cứ thực hành nói chung, A10 chỉ định sổ xác nhận sử dụng phòng máy phân tích dữ liệu. Không coi chúng là hai lần bắt nộp cùng một hồ sơ nếu chưa có nguồn nói vậy.

### Ba cột năm 2027 và phần loại trừ

| Cột | Header đọc từ Structured Document | Quan hệ được nguồn hỗ trợ |
|---|---|---|
| c10 | 2027 / Quy mô / Chỉ tiêu (SV) | A02/A08: dự kiến của 2027. Không đổi thành “Ước tính” hoặc tự nghiệm thu. |
| c11 | 2027 / Dự kiến / Ước tính (SV) | A02/A08 + **A11**: đúng đại lượng Ước tính. |
| c12 | 2027 / Ước đạt / Tỷ lệ (%) | A02/A08; A09 về tỷ lệ cùng năm. Không nhận riêng A11 chỉ vì cùng nhóm năm. |
| c05 | 2025 / Ghi nhận / Số lượng (SV) | A06 về mốc 2025; bị A11 loại trừ. |
| c08 | 2026 / Ghi nhận / Số lượng (SV) | A07 về mốc chốt tạm; bị A11 loại trừ. |

“Không nhận A11” không có nghĩa c10/c12 là đã nghiệm thu: tình trạng dự kiến của chúng được A02/A08 giữ độc lập. c06/c09/c12 là ba cột tỷ lệ; áp A09 đúng năm của từng cột, không lấy số lượng khác năm làm mẫu số/tử số. Báo cáo không kiểm lại phép tính từng dòng.

### Ngoại lệ nhóm A và B

| Thuộc tính | Nhóm A — A03 | Nhóm B — A05 |
|---|---|---|
| Tập chương trình | r001–r006; không gồm dòng tổng r013 | r007–r012; không gồm r013 |
| Loại hồ sơ | Xác nhận thiết bị/phòng thực hành | Minh chứng thực tập ngoài trường |
| Mốc/phạm vi | Chỉ kế hoạch 2027 | Đúng kỳ thực tập theo điều kiện nguồn; không suy mọi hồ sơ/năm đều hợp lệ |
| Hạn | ≤15 **ngày làm việc**, từ hạn xác nhận ban đầu | ≤30 ngày, từ ngày kết thúc đợt thực tập |
| Hồ sơ bổ trợ | Thông báo lịch kiểm định trùng đợt khóa dự kiến và quyết định gia hạn của Phòng Đào tạo | Nhật ký cá nhân, xác nhận giảng viên cùng kỳ, biên bản trực tuyến của đơn vị có thẩm quyền cùng lịch/danh sách người xác nhận |
| Loại trừ | Nhóm B; số người học 2025, số ghi nhận 2026; không sửa chỉ tiêu hoặc quyết định kinh phí | Nhóm A; không miễn an toàn; quá hạn thiếu xác nhận cuối cùng thì trở lại “Cần bổ sung hồ sơ” |

Thời hạn thẩm định lại 30 ngày tại l012 khoản2 là một quy trình khác thời hạn tạm thay chữ ký 30 ngày tại II.2. Không nhập hai mốc này thành một ngoại lệ chung.

## 8. Có mục trùng hoặc bị thay thế không?

| Cặp/nhóm | Loại chồng lấp | Kết luận |
|---|---|---|
| O01 ↔ A10; O02 ↔ A11 | Dùng lại issue nguồn/đích chính xác | Đã tránh sinh thêm hai scope issue. Không có xóa/thay issue. |
| O03 ↔ O04/O05 | Heading/điều chứa body đã có issue riêng | Trùng lượt đọc, không trùng ID. Có thể nhóm hiển thị “Điều15”, giữ quyết định từng câu hỏi; hiện chưa có reconciliation thay thế. |
| O06 ↔ O07 | O06 dẫn nhập cả hai ngoại lệ, O07 đi sâu nhóm B | Có phần bằng chứng dùng chung, chưa đủ để xóa O06 vì còn nhóm A và giới hạn không nhập ngoại lệ. |
| O08 ↔ S10 | Cùng footnote, một mục reference và một mục scope c02/ba dòng | Có thể đối chiếu chung; một quyết định không tự đóng mục còn lại. |
| S04/A04 ↔ O01/A10 | Cùng AM-0007, yêu cầu tổng quát và yêu cầu hồ sơ cụ thể | Không phải duplicate nguyên nghĩa; giữ cả phủ định AM-0070. |
| S02/A02 ↔ S08/A08 ↔ O02/A11 | Chung năm 2027, khác trạng thái/ngày lập/đại lượng | Bổ sung cho nhau; không gộp thành một rule cho ba cột. |

**Số duplicate kỹ thuật đã thấy: 0 issue ID bị lặp; 0 xác nhận mới thừa trên cùng assertion ID; 0 mục được thay thế chính thức.** Có chồng lấp nội dung và gánh nặng duyệt như bảng trên. Mã [tạo scope issue](../../../backend/app/modules/knowledge/services/semantic_assertions.py:64) dùng lại O01/O02 khi full-source và đích trùng; mã [reconciliation](../../../backend/app/modules/knowledge/services/semantic_context_review.py:85) không tự đóng issue khi chỉ bị bỏ khỏi câu trả lời mới.

Mã [tổng hợp trạng thái](../../../backend/app/modules/knowledge/services/semantic_context_review.py:136) và [guard áp dụng](../../../backend/app/modules/knowledge/services/semantic_context_review.py:197) vẫn yêu cầu toàn proposal hết blocker. Nếu về sau muốn áp dụng từng nhóm quan hệ, cần một phạm vi thay đổi riêng có chứng minh persistence/revision, không được chỉ bỏ những issue còn mở khỏi danh sách.

## 9. Bảng hỗ trợ bạn quyết định

Đây là phương án trình xem, không phải quyết định đã nhập vào hệ thống.

| Nhóm cần xem | Mục/quan hệ | Đề nghị hiện tại | Điều cần bạn lựa chọn |
|---|---|---|---|
| Quy định rõ nguồn/đích | S01,S02,S04,S06,S07,S08,S09,S10; O01,O02 | Có thể đối chiếu từng scope/điều kiện. S09 giữ nghĩa tỷ lệ, S10 giữ đúng tập mã. | Chấp nhận quy tắc đã mô tả hoặc yêu cầu sửa từng mục; không biến ghi chú này thành approval hàng loạt. |
| Hồ sơ thiết bị A | **S03/A03**, phần A của O05/O06 | **Tạm chưa xác nhận scope c10/c11/c12.** | Chọn yêu cầu chỉnh đích hồ sơ/ngữ cảnh trước, hoặc cung cấp căn cứ cho cách gắn cột; nếu đổi phải có hash mới. |
| Ngoại lệ B | **S05/A05**, O04/O06/O07 và body liên quan ở O03/O05 | Đủ văn bản để trình quy tắc có điều kiện. | Xem riêng từng điều kiện, giới hạn 30 ngày, hồ sơ thay thế và loại nhóm A/an toàn. Không xác nhận thực tế mọi hồ sơ đều đủ điều kiện. |
| Phạm vi reference còn rộng | **O03/O04/O05** | Đề nghị yêu cầu thu hẹp/giải thích mapping trước khi coi các reference chi phối toàn bảng. | Tách trực tiếp/bảo vệ/có điều kiện theo mục4–6; không chọn “không liên quan” cho cả reference chỉ vì một vài quan hệ không chịu chi phối. |
| Footnote/định danh | **O08 + S10**, liên quan S04/O01 | Đủ căn cứ; có thể đọc cùng nhóm. | Giữ mã dạng chuỗi, đúng row IDs; từng ID quyết định vẫn riêng. |

**11 quan hệ có thể trình đọc riêng không có nghĩa toàn proposal đã đủ để duyệt một lần.** A03 và cách biểu diễn liên kết O03/O04/O05 vẫn cần làm rõ. Nếu tạo proposal sửa tiếp, phải có hash mới và giữ cả bản gốc lẫn bản 12 quan hệ hiện tại để audit; báo cáo này chưa tạo bản sửa như vậy.

## 10. Dọn Storage tạm an toàn, giữ chính sách bảo vệ

Đường dẫn đã kiểm tra:

`D:\DuAnPhanMem\qnu-ai-platform\backend\storage\context548-runtime-eba155eff9ff`

| Kiểm tra chỉ đọc trong lượt này | Kết quả |
|---|---|
| Khớp đường dẫn runtime trong state của lượt test, dưới đúng repo/backend/storage | Đạt; tên DB cũ khớp nonce của state |
| Số tệp/dung lượng | **3.230 tệp, 48.570.307 byte, khoảng 46,3 MiB** tại thời điểm kiểm kê |
| Symlink/junction/reparse point | 0 |
| Tệp có nhiều hardlink | 0 |
| Git theo dõi tệp trong runtime | 0; bị ignore bởi `.gitignore` dòng112 |
| Tiến trình Python tham chiếu runtime hoặc lượt test Context553 | Không thấy tại thời điểm kiểm tra; không phải cam kết rằng sau này không có tiến trình mới |
| Checkpoint gốc/revised có tham chiếu basename runtime trong JSON/MD | Không thấy; hai checkpoint nằm ở thư mục khác, giữ object sources riêng |
| DB test | Receipt trước ghi đã xóa và kiểm vắng; lượt này không kết nối DB để kiểm lại |
| Dọn Storage thực tế trong lượt này | **NOT RUN**, chỉ kiểm kê và đưa phương án |

Runtime gồm các basetemp pytest, bản sao mã baseline và object fixture test; không phải thư mục storage nguồn đang chạy. Báo cáo/manifest/evidence đã xuất ở thư mục riêng. Những thư mục **phải giữ** gồm checkpoint552, `context553-review-final`, các bản revised trung gian nếu còn cần audit và thư mục evidence/báo cáo; không chọn `backend/storage` cha để dọn.

**Phương án an toàn cho người dùng:**

1. Đối chiếu lại exact đường dẫn trên, state `database_removed_storage_pending` và bảo đảm không có lượt test mới dùng nó.
2. Giữ báo cáo/bằng chứng cùng checkpoint ở các vị trí riêng đã dẫn; nếu vẫn cần tra basetemp/bản mã baseline thô thì lưu bản cần dùng trước khi dọn.
3. Trong Windows File Explorer, chọn đúng thư mục có hậu tố `eba155eff9ff`, dùng **Delete để đưa vào Thùng rác**, kiểm lại hộp thoại; không chọn thư mục cha và không dùng Shift+Delete. Đây là thao tác người dùng trên thư mục test đã xác minh, có khả năng phục hồi theo thiết lập Thùng rác/ổ đĩa. Nếu Windows cho biết sẽ xóa vĩnh viễn thay vì đưa vào Thùng rác, dừng để chọn cách sao lưu được phép trước.
4. Nếu vẫn bị chính sách/quyền chặn, dừng và nhờ người quản trị xử lý đúng thư mục qua quy trình được cho phép. Không tắt sandbox, approval policy, đổi shell hoặc dùng công cụ khác để né chặn.
5. Sau khi đã thực hiện bằng đường được phép, kiểm đường dẫn không còn tồn tại rồi mới ghi `storage_removed=true`. Hiện chưa ghi trạng thái này.

Lượt trước, kiểm duyệt tự động đã từ chối recursive delete, gồm cả exact literal path, với lý do **“blocked by policy”**. Lượt này không gọi lại lệnh xóa, không tắt/bỏ qua chính sách và không nhận cleanup là PASS.

## 11. Phạm vi kiểm chứng của báo cáo này

Đã kiểm manifest, hash proposal/input, exact evidence spans, đích dòng/cột và các liên kết từ JSON hiện có; đọc đúng đoạn nguồn và mã guard. Có đối soát ID theo cả hai chiều và kiểm kê runtime chỉ đọc.

Không gọi lại LLM; không import/chạy pipeline ứng dụng; không apply, approve, rebuild, publish, reindex, migration hoặc chạy lại toàn tài liệu. Không sửa mã nguồn. Các kết quả 261 focused PASS, 18 frontend PASS và full18FAIL/2398PASS/17SKIP là **lịch sử Context553**, không phải test chạy lại trong lượt báo cáo này.

Nguồn để bạn đọc tiếp: [bản gốc](../../../backend/storage/context552-checkpoint-06689f8f17dc/REVIEW.md), [proposal 12 quan hệ](../../../backend/storage/context553-review-final/proposal.json), [context đầy đủ](../../../backend/storage/context553-review-final/review-context.json), [bản đọc có trích đoạn](../../../backend/storage/context553-review-final/REVIEW.md). Mọi quyết định thật sau này phải kiểm actor/quyền server, đúng source/revision/hash; file báo cáo không cấp quyền và không chứa quyết định ứng dụng.

## Phụ lục — ID thực tế

Phần dưới được xuất trực tiếp từ checkpoint, nối nhãn O/S/A của báo cáo với ID thật; không tạo hoặc thay ID.

### Tám issue gốc

| Nhãn | Nguồn | ID thật |
|---|---|---|
| O01 | qnu:p050 | `ctxissue:caaaec699ea13848e145573699939a54240f13984efbc7b77767fd164ec32a6d` |
| O02 | qnu:p051 | `ctxissue:7796dfd6b7e8ef92fea6bf823a8618825a249295d3404d17d8716d9d6b4ff3fb` |
| O03 | qnu:s030 | `ctxissue:020f5d0bffea6fabb4605e5fb4c53ccd72fb7320a3cf354dd477b5b81000a21e` |
| O04 | qnu:l012 | `ctxissue:081d95e2e836c4aad52bfa72977575c1e7c732c094cffc52c9d42cc4c9fb26c4` |
| O05 | qnu:p084 | `ctxissue:d62e3952982928c38fa242bf17a7cf867f7ffdceb5f4599915d9260884e65530` |
| O06 | qnu:p090 | `ctxissue:8e49ed2d0da6280c39ddd1f068fe53c891bed6999eb732e92cd8214758ec9c11` |
| O07 | qnu:s036 | `ctxissue:54652f308c332f02a379469f0d2ee9fc8f62a858dbc4ac98fb0d8adc515d9bda` |
| O08 | qnu:docx_footnote_2 | `ctxissue:891a560adef9b2010117727e0188690b2d36c25c0dda4d594ebe58456cd9920d` |

### Mười xác nhận mới

| Nhãn | Quan hệ | ID thật |
|---|---|---|
| S01 | A01 | `ctxissue:8c74cecc6c1de94bac3715d48d783e4d7975188f749d9e681ae8988e5c4011a3` |
| S02 | A02 | `ctxissue:ee53a5c2d8f121596b5bb8f81c1e93044a89c36656a8eab14375b5e727f29b15` |
| S03 | A03 | `ctxissue:8c14350a7e481cb5770d82b46947e8b3557fc0ddf015507eb2fd5d4c9d0170d2` |
| S04 | A04 | `ctxissue:f026c80a950ff10430b7b31e7b146b5014f81deeba899ed8b4af776fc79129fa` |
| S05 | A05 | `ctxissue:8366568b67932170f56e7728d71dbe61e463cb0ef213ff43ad7c42de4c4dbc8a` |
| S06 | A06 | `ctxissue:7b65a696f23638a4fa87a3096380e020d4bc1a15ecad40472fd8b3356974f812` |
| S07 | A07 | `ctxissue:b0fd1ca47916f488a8d360129770b19894f89670f5e6ef4937cf30b97bdcc544` |
| S08 | A08 | `ctxissue:34fa2d9f090fc7934c168680a8d3ce0858e3263f2b8f71c830e71ad686fbfb84` |
| S09 | A09 | `ctxissue:13adc3149f8c41067159b8b17fdde7c5a5b64f9738f430d5089d401814ad3e3c` |
| S10 | A12 | `ctxissue:f5535089659a575c39048156c03ab3a3bcb59bf6f673873b56f4d632413a600a` |

### Mười hai assertion ID

| Quan hệ | Assertion ID |
|---|---|
| A01 | `assertion:ef2f233670f3db45390c35d7d5eb9d2297a04865515607a190e1334f8bb2c111` |
| A02 | `assertion:97deb454b96a5f242838c41f6c6402ee9c24fd83d1820ca663af3664c2082025` |
| A03 | `assertion:353338132c32a2c1d4f5ba31a8892fa160d64b92d93acb58460bef6bdd289cea` |
| A04 | `assertion:304cdcdb31c9140ff804cb343f9e0903524faa1cf28c1a25b71cd6294fa620f5` |
| A05 | `assertion:17e7f93a4b457aad45d9bf1f24cc3ee7ef3a519e99a30973331c7b636d8a5652` |
| A06 | `assertion:d85bf67d55be5465b9b978fdcda554eeca14de39784cf5dfb7e1e1d1af7390cb` |
| A07 | `assertion:33f215deea2d7bf1835df650f0af030db8c269613ad8d45c9eb12b5a563c764f` |
| A08 | `assertion:0c5e6143d21f8fb70a9a9603ed89b519011229f8831d9072d75884b516856339` |
| A09 | `assertion:e4c57a8a772072df85ff9ed146e9e86f441432d9106d66a79610cc6d238508da` |
| A10 | `assertion:aa21305077e70d79c66e1fa6331922ca10c76a1c945e3da03b04887b2e07ded9` |
| A11 | `assertion:95980004d5efeafe34f968d53da058e2d080cff2d443cdfd488e7529c529d974` |
| A12 | `assertion:1041672374d1a5525a977ef14d54835158dd7507f151e9671a002f092220b6fc` |
