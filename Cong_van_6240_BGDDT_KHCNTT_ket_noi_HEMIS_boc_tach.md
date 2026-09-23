# CÔNG VĂN SỐ 6240/BGDĐT-KHCNTT — HƯỚNG DẪN KẾT NỐI API, ĐỒNG BỘ DỮ LIỆU HEMIS

| **BỘ GIÁO DỤC VÀ ĐÀO TẠO** <br><br> Số: 6240 /BGDĐT-KHCNTT <br> V/v hướng dẫn kết nối API, đồng bộ dữ liệu với Hệ thống cơ sở dữ liệu về giáo dục đại học (HEMIS) | **CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM** <br> **Độc lập - Tự do - Hạnh phúc** <br><br> *Hà Nội, ngày 15 tháng 09 năm 2026* |
| :--- | :--- |

> **TRƯỜNG ĐẠI HỌC QUY NHƠN**  
> **ĐẾN** Số: 1998  
> Ngày: 15/9/2026  
> Chuyển: ...........................................  
> Số và ký hiệu HS: ...............................  

**Kính gửi:**
- Các bộ, cơ quan ngang bộ, Ủy ban nhân dân các tỉnh, thành phố và các cơ quan, tổ chức quản lý trực tiếp cơ sở giáo dục đại học;
- Các cơ sở giáo dục đại học; các cơ sở giáo dục khác có đào tạo trình độ giáo dục đại học.

Thực hiện Kế hoạch số 1496/KH-BGDĐT ngày 23/7/2026 của Bộ Giáo dục và Đào tạo về hành động 100 ngày xử lý các điểm nghẽn về chuyển đổi số; Thông báo số 424/TB-VPCP ngày 14/8/2026 của Văn phòng Chính phủ về kết luận của Phó Thủ tướng Chính phủ Lê Tiến Châu tại cuộc họp với Bộ Giáo dục và Đào tạo về công tác chuyển đổi số; nhằm nâng cao chất lượng, tính đầy đủ, chính xác và kịp thời của dữ liệu trên Hệ thống cơ sở dữ liệu về giáo dục đại học (HEMIS), Bộ Giáo dục và Đào tạo (GDĐT) hướng dẫn các cơ sở đào tạo triển khai kết nối API, đồng bộ dữ liệu với HEMIS như sau:

### 1. Nguyên tắc kết nối, đồng bộ dữ liệu

- Các cơ sở đào tạo chủ động tổ chức kết nối hệ thống quản lý, cơ sở dữ liệu của đơn vị với HEMIS thông qua API theo tài liệu kỹ thuật, cấu trúc dữ liệu và phương thức kết nối do Bộ GDĐT cung cấp.
- Việc kết nối, đồng bộ phải bảo đảm dữ liệu trên HEMIS đúng, đủ, sạch, sống, thống nhất, phản ánh đúng tình trạng thực tế tại cơ sở đào tạo; hạn chế nhập liệu thủ công, trùng lặp dữ liệu và nâng cao khả năng cập nhật thường xuyên.
- Cơ sở đào tạo thực hiện ký số dữ liệu trước khi đồng bộ qua API. Người đứng đầu cơ sở đào tạo chịu trách nhiệm về tính đầy đủ, chính xác, thống nhất và kịp thời của dữ liệu được đồng bộ.

### 2. Nội dung triển khai

**a) Rà soát, chuẩn bị điều kiện kết nối**
- Các cơ sở đào tạo rà soát hệ thống phần mềm, cơ sở dữ liệu hiện đang sử dụng; bố trí đầu mối nghiệp vụ và đầu mối kỹ thuật để tổ chức kết nối, đồng bộ dữ liệu với HEMIS.
- Rà soát, chuẩn hóa dữ liệu tại hệ thống nguồn, trong đó tập trung vào các nhóm dữ liệu về cơ sở đào tạo; ngành đào tạo; chương trình đào tạo; người học; đội ngũ; hoạt động đào tạo và các nhóm dữ liệu khác thuộc phạm vi HEMIS.

**b) Thực hiện kết nối và đồng bộ dữ liệu**
- Căn cứ tài liệu kỹ thuật API do Bộ GDĐT cung cấp, các cơ sở đào tạo thực hiện ánh xạ các trường dữ liệu giữa hệ thống của đơn vị và HEMIS; tổ chức kiểm thử kết nối, truyền nhận dữ liệu và xử lý các lỗi phát sinh trước khi thực hiện đồng bộ chính thức.
- Dữ liệu đồng bộ phải tuân thủ cấu trúc, danh mục dùng chung, mã định danh và các quy tắc kiểm tra dữ liệu của HEMIS (tài liệu đặc tả kèm theo).
- Đối với dữ liệu người học, đội ngũ và thông tin cơ sở đào tạo, cần ưu tiên rà soát, chuẩn hóa thông tin định danh, bảo đảm điều kiện thực hiện đối soát, xác thực và gắn mã định danh theo quy định.

**c) Kiểm tra, đối soát sau đồng bộ**
Sau mỗi đợt đồng bộ, cơ sở đào tạo thực hiện kiểm tra kết quả tiếp nhận dữ liệu trên HEMIS; đối soát với dữ liệu tại hệ thống nguồn và kịp thời xử lý các bản ghi bị lỗi, thiếu thông tin, không thống nhất hoặc không đáp ứng yêu cầu xác thực.

### 3. Bảo đảm an toàn, bảo mật trong kết nối

- Các cơ sở đào tạo có trách nhiệm quản lý, bảo mật tài khoản và thông tin phục vụ kết nối API; không chia sẻ tài khoản, thông tin xác thực kết nối cho tổ chức, cá nhân không có trách nhiệm.
- Việc kết nối, khai thác, truyền nhận dữ liệu phải tuân thủ các quy định về an toàn thông tin mạng, an ninh mạng, bảo vệ dữ liệu cá nhân và các quy định pháp luật có liên quan.
- Các cơ sở đào tạo cần có cơ chế ghi nhận nhật ký kết nối, theo dõi trạng thái đồng bộ và lưu thông tin lỗi để phục vụ kiểm tra, đối soát và xử lý sự cố khi cần thiết.

### 4. Tổ chức thực hiện

- Đề nghị các cơ quan quản lý trực tiếp cơ sở giáo dục đại học phối hợp chỉ đạo, kiểm tra, đôn đốc các cơ sở đào tạo thuộc phạm vi quản lý triển khai kết nối, đồng bộ dữ liệu với HEMIS.
- Các cơ sở giáo dục đại học khẩn trương thực hiện, bố trí nguồn lực, rà soát hệ thống và phối hợp với Bộ GDĐT (Cục Khoa học, Công nghệ và Thông tin) để triển khai kết nối API; báo cáo kết quả thực hiện, tiến độ triển khai và các khó khăn, vướng mắc phát sinh trong quá trình thực hiện kết nối **trước ngày 30/9/2026** (theo mẫu báo cáo gửi kèm tại phụ lục); đồng thời tiếp tục thực hiện rà soát, cập nhật, làm sạch, xác nhận và ký số dữ liệu trên HEMIS, bảo đảm tiến độ thực hiện Kế hoạch số 1496/KH-BGDĐT.
- Đối với các khó khăn, vướng mắc về nội dung, nghiệp vụ dữ liệu giáo dục đại học, đề nghị phản ánh về Vụ Giáo dục Đại học (ông Phan Thế Hùng, chuyên viên chính Vụ Giáo dục Đại học, email: `pthung@moet.gov.vn`, ĐT: `0904.896.868`) để phối hợp xử lý.
- Đối với các nội dung liên quan đến tài khoản kết nối, đồng bộ dữ liệu và các vấn đề kỹ thuật của HEMIS, đề nghị liên hệ Cục Khoa học, Công nghệ và Thông tin (ông Nguyễn Quang Huy, thư điện tử: `nqhuy.cit@moet.edu.vn`, điện thoại: `0364.714.702`) để được hướng dẫn, hỗ trợ.

Bộ Giáo dục và Đào tạo trân trọng cám ơn./.

<br>

| **Nơi nhận:** | **KT. BỘ TRƯỞNG** <br> **THỨ TRƯỞNG** |
| :--- | :--- |
| - Như trên;<br>- Bộ trưởng (để b/c);<br>- Các Thứ trưởng;<br>- Vụ GDĐH (để thực hiện);<br>- Trung tâm Dữ liệu giáo dục (để thực hiện);<br>- Lưu: VT, KHCNTT. | *(Đã ký, đóng dấu)* <br><br><br> **Phạm Quang Hưng** |

<br>

---

## Phụ lục: [MẪU] BÁO CÁO KẾT QUẢ TRIỂN KHAI KẾT NỐI, ĐỒNG BỘ DỮ LIỆU VỚI HEMIS
*(Kèm theo Công văn số 6240 /BGDĐT-KHCNTT ngày 15 tháng 09 năm 2026 của Bộ GDĐT)*

### I. THÔNG TIN CHUNG

1. Tên cơ sở đào tạo: .......................................................................................
2. Mã cơ sở đào tạo trên HEMIS: ..........................................................................
3. Đơn vị đầu mối thực hiện: ..............................................................................
4. Đầu mối liên hệ về kỹ thuật:
- Họ và tên: .................................................................................................
- Chức vụ/đơn vị: ............................................................................................
- Số điện thoại: ..............................................................................................
- Email: ......................................................................................................

### II. TÌNH HÌNH VÀ KẾT QUẢ TRIỂN KHAI KẾT NỐI API

**1. Tình hình rà soát hệ thống**
- Đã rà soát hệ thống/cơ sở dữ liệu hiện có của cơ sở đào tạo: □ Đã thực hiện &nbsp;&nbsp;&nbsp;&nbsp; □ Chưa thực hiện.
- Đã rà soát, đối chiếu cấu trúc, trường dữ liệu phục vụ kết nối với HEMIS: □ Đã thực hiện &nbsp;&nbsp;&nbsp;&nbsp; □ Chưa thực hiện.
- Đánh giá mức độ sẵn sàng về hạ tầng, nhân lực và hệ thống phục vụ kết nối:  
.................................................................................................................

**2. Tình hình triển khai kết nối API**
- Đã bố trí nhân lực thực hiện kết nối: □ Có &nbsp;&nbsp;&nbsp;&nbsp; □ Chưa.
- Đã thực hiện cấu hình/kết nối API: □ Hoàn thành &nbsp;&nbsp;&nbsp;&nbsp; □ Đang thực hiện &nbsp;&nbsp;&nbsp;&nbsp; □ Chưa thực hiện.
- Thời điểm bắt đầu triển khai: ....../....../2026.
- Thời điểm hoàn thành dự kiến/thực tế: ....../....../2026.
- Trạng thái kết nối hiện tại: □ Kết nối thành công &nbsp;&nbsp;&nbsp;&nbsp; □ Đang kiểm thử &nbsp;&nbsp;&nbsp;&nbsp; □ Đang khắc phục lỗi &nbsp;&nbsp;&nbsp;&nbsp; □ Chưa kết nối được.

**3. Kết quả đồng bộ dữ liệu**
.................................................................................................................
.................................................................................................................

### III. KHÓ KHĂN, VƯỚNG MẮC TRONG QUÁ TRÌNH THỰC HIỆN

1. **Về nguồn lực triển khai:**  
.................................................................................................................

2. **Về hạ tầng kỹ thuật, hệ thống phần mềm:**  
.................................................................................................................

3. **Về dữ liệu và chất lượng dữ liệu:**  
.................................................................................................................

4. **Về kết nối API, đồng bộ dữ liệu:**  
.................................................................................................................

5. **Về thực hiện ký số dữ liệu:**  
.................................................................................................................

6. **Các khó khăn, vướng mắc khác:**  
.................................................................................................................

### IV. KIẾN NGHỊ, ĐỀ XUẤT

1. .................................................................................................................
2. .................................................................................................................
3. .................................................................................................................

<br>

| | **THỦ TRƯỞNG ĐƠN VỊ** <br> *(Ký, ghi rõ họ tên, đóng dấu)* |
| :--- | :--- |
| | *(Ký tên và đóng dấu)* <br><br><br> |

<!-- Trang 6: Trang trắng (Blank scan page - không chứa nội dung văn bản) -->
