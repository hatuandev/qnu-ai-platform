"""Seed data for official QNU Library & Digital Learning Resources Knowledge (Cẩm nang Thư viện ĐH Quy Nhơn)."""

from __future__ import annotations

from typing import Any

LIBRARY_DOCUMENT_ID = "doc_qnu_cam_nang_thu_vien"
LIBRARY_COLLECTION_ID = "col_library"
LIBRARY_TITLE = "Cẩm nang Trung tâm Thông tin - Thư viện và Khai thác Học liệu số Trường Đại học Quy Nhơn"
LIBRARY_FILENAME = "Cam_nang_thong_tin_thu_vien_va_hoc_lieu_so_QNU.pdf"

LIBRARY_CHUNKS: list[dict[str, Any]] = [
    {
        "id": "chk_lib_1",
        "chunk_index": 0,
        "title": "Phần I: Giới thiệu chung, Địa chỉ, Hotline và Thời gian mở cửa Thư viện",
        "content": (
            "TRUNG TÂM THÔNG TIN - THƯ VIỆN TRƯỜNG ĐẠI HỌC QUY NHƠN\n"
            "Phần I - THÔNG TIN CHUNG VÀ THỜI GIAN HOẠT ĐỘNG:\n"
            "1. Tên đơn vị: Trung tâm Thông tin - Thư viện Trường Đại học Quy Nhơn.\n"
            "2. Địa điểm: Tòa nhà Thư viện 4 tầng hiện đại, diện tích sàn trên 4.500 m2, nằm ngay trung tâm khuôn viên Trường Đại học Quy Nhơn, số 170 An Dương Vương, thành phố Quy Nhơn, tỉnh Bình Định.\n"
            "3. Điện thoại đường dây nóng hỗ trợ: 0256.3846.888.\n"
            "4. Email tiếp nhận yêu cầu và hỗ trợ bạn đọc: thuvien@qnu.edu.vn.\n"
            "5. Cổng thông tin tra cứu mục lục trực tuyến (OPAC) và thư viện số: https://lib.qnu.edu.vn.\n"
            "6. Thời gian phục vụ các phòng đọc và mượn trả tài liệu: Từ Thứ Hai đến Thứ Bảy hàng tuần:\n"
            "   - Buổi sáng: Từ 7h00 đến 11h30.\n"
            "   - Buổi chiều và tối: Từ 13h30 đến 21h00.\n"
            "   - Riêng Khu tự học thông minh có máy lạnh, ổ cắm điện và wifi tốc độ cao: Mở cửa phục vụ 24/7 (kể cả Chủ nhật và ngày lễ) cho sinh viên và học viên của trường."
        ),
        "metadata": {
            "section": "Phần I",
            "topic": "Thông tin chung & Thời gian mở cửa",
            "document_name": LIBRARY_FILENAME,
            "title": LIBRARY_TITLE,
            "page": 1,
        },
    },
    {
        "id": "chk_lib_2",
        "chunk_index": 1,
        "title": "Phần II: Thẻ thư viện, Đối tượng phục vụ và Tài khoản Thư viện số",
        "content": (
            "Phần II - THẺ BẠN ĐỌC VÀ TÀI KHOẢN TRUY CẬP THƯ VIỆN SỐ:\n"
            "1. Đối tượng phục vụ: Toàn thể cán bộ, giảng viên, nghiên cứu sinh, học viên cao học và sinh viên các hệ đào tạo chính quy của Trường Đại học Quy Nhơn.\n"
            "2. Thẻ thư viện tích hợp:\n"
            "   - Sinh viên và học viên sử dụng Thẻ sinh viên tích hợp mã vạch Barcode/RFID làm thẻ thư viện chính thức để quét qua cổng an ninh kiểm soát và mượn trả tài liệu.\n"
            "   - Thẻ được kích hoạt tự động ngay sau khi hoàn thành thủ tục nhập học đầu khóa, không thu thêm phí làm thẻ bạn đọc.\n"
            "3. Tài khoản thư viện số và dịch vụ trực tuyến:\n"
            "   - Tài khoản đăng nhập cổng tra cứu https://lib.qnu.edu.vn được đồng bộ thông qua hệ thống định danh Single Sign-On (SSO) bằng tài khoản email chính thức @qnu.edu.vn.\n"
            "   - Nghiêm cấm việc cho mượn thẻ sinh viên hoặc chia sẻ tài khoản thư viện số cho người ngoài trường.\n"
            "   - Trường hợp bị mất thẻ sinh viên, bạn đọc phải báo ngay cho Thư viện qua email thuvien@qnu.edu.vn hoặc liên hệ trực tiếp tại Quầy thủ thư Tầng 1 để tạm khóa tài khoản mượn sách."
        ),
        "metadata": {
            "section": "Phần II",
            "topic": "Thẻ thư viện & Tài khoản SSO",
            "document_name": LIBRARY_FILENAME,
            "title": LIBRARY_TITLE,
            "page": 2,
        },
    },
    {
        "id": "chk_lib_3",
        "chunk_index": 2,
        "title": "Phần III: Quy định Mượn - Trả sách in, Hạn mức, Gia hạn và Phí phạt quá hạn",
        "content": (
            "Phần III - QUY ĐỊNH MƯỢN TRẢ TÀI LIỆU VÀ GIÁO TRÌNH IN:\n"
            "1. Hạn mức và thời gian mượn tài liệu về nhà:\n"
            "   - Sinh viên đại học chính quy: Được mượn tối đa 5 cuốn sách/giáo trình cùng một thời điểm; Thời hạn mượn tối đa là 14 ngày/lần mượn.\n"
            "   - Học viên cao học và nghiên cứu sinh: Được mượn tối đa 10 cuốn sách/tài liệu; Thời hạn mượn tối đa là 30 ngày/lần mượn.\n"
            "   - Cán bộ, giảng viên của trường: Được mượn tối đa 15 cuốn sách phục vụ giảng dạy và nghiên cứu; Thời hạn mượn theo học kỳ (tối đa 90 ngày).\n"
            "2. Quy định gia hạn tài liệu mượn:\n"
            "   - Mỗi cuốn sách được phép gia hạn trực tuyến 1 lần với thời gian thêm là 7 ngày thông qua cổng https://lib.qnu.edu.vn, với điều kiện cuốn sách đó chưa có bạn đọc khác đặt trước (hold).\n"
            "3. Xử lý tài liệu quá hạn và làm mất, hư hỏng:\n"
            "   - Mức phí phạt quá hạn mượn sách: 2.000 đồng/cuốn/ngày quá hạn. Bạn đọc phải thanh toán phí quá hạn mới được tiếp tục mượn tài liệu mới.\n"
            "   - Trường hợp làm mất sách hoặc làm rách nát, hư hỏng không thể sử dụng: Bạn đọc phải đền cuốn sách mới đúng nguyên bản (cùng tên, tác giả, nhà xuất bản) hoặc bồi thường số tiền bằng 2 lần giá trị bìa sách theo thị trường."
        ),
        "metadata": {
            "section": "Phần III",
            "topic": "Mượn trả & Phí quá hạn",
            "document_name": LIBRARY_FILENAME,
            "title": LIBRARY_TITLE,
            "page": 3,
        },
    },
    {
        "id": "chk_lib_4",
        "chunk_index": 3,
        "title": "Phần IV: Khai thác Cơ sở dữ liệu điện tử quốc tế & Học liệu số",
        "content": (
            "Phần IV - KHAI THÁC CƠ SỞ DỮ LIỆU ĐIỆN TỬ VÀ HỌC LIỆU SỐ:\n"
            "1. Danh mục các Cơ sở dữ liệu (CSDL) học thuật trực tuyến có bản quyền:\n"
            "   - CSDL ScienceDirect (Elsevier): Trên 2.500 tạp chí khoa học toàn văn thuộc các khối ngành Tự nhiên, Công nghệ, Y sinh và Kinh tế.\n"
            "   - CSDL Thư mục Scopus: Phục vụ tra cứu trích dẫn, chỉ số Hirsch (h-index) và xếp hạng công bố quốc tế.\n"
            "   - CSDL IEEE Xplore: Hơn 5 triệu tài liệu hội thảo và tạp chí kỹ thuật chuyên ngành Công nghệ thông tin, Điện tử viễn thông, Trí tuệ nhân tạo.\n"
            "   - CSDL SpringerLink và ProQuest: Cung cấp hàng trăm nghìn sách điện tử (E-book) và luận án tiến sĩ quốc tế.\n"
            "   - CSDL Tạp chí Khoa học Việt Nam trực tuyến (VJOL): Toàn văn các bài báo khoa học xuất bản trong nước.\n"
            "2. Phương thức truy cập CSDL điện tử:\n"
            "   - Truy cập trực tiếp: Kết nối mạng wifi hoặc mạng dây nội bộ trong khuôn viên Trường Đại học Quy Nhơn (nhận diện qua dải IP của trường).\n"
            "   - Truy cập từ xa ngoài trường (Off-campus Access): Đăng nhập qua cổng Proxy/VPN tại địa chỉ https://lib.qnu.edu.vn bằng tài khoản SSO @qnu.edu.vn.\n"
            "3. Kho học liệu số nội sinh của trường: Bao gồm hơn 12.000 luận văn thạc sĩ, luận án tiến sĩ và đề tài nghiên cứu khoa học các cấp bảo vệ tại ĐH Quy Nhơn."
        ),
        "metadata": {
            "section": "Phần IV",
            "topic": "CSDL điện tử & Học liệu số",
            "document_name": LIBRARY_FILENAME,
            "title": LIBRARY_TITLE,
            "page": 4,
        },
    },
    {
        "id": "chk_lib_5",
        "chunk_index": 4,
        "title": "Phần V: Nội quy Phòng đọc, Khu Tự học và Đặt phòng Thảo luận nhóm",
        "content": (
            "Phần V - NỘI QUY PHÒNG ĐỌC VÀ KHU VỰC THẢO LUẬN NHÓM:\n"
            "1. Nội quy phòng đọc sách và nghiên cứu cá nhân:\n"
            "   - Xuất trình thẻ sinh viên/cán bộ khi vào thư viện; gửi balô, túi xách đúng tủ đồ cá nhân tại sảnh Tầng 1.\n"
            "   - Giữ trật tự tuyệt đối, chuyển điện thoại sang chế độ rung, không nói chuyện lớn tiếng hay gây ồn ào.\n"
            "   - Không mang đồ ăn, nước ngọt có đường vào phòng đọc; chỉ được phép mang chai nước lọc có nắp đậy kín.\n"
            "   - Không tự ý mang tài liệu đọc tại chỗ (từ điển, báo, tạp chí số mới, tài liệu quý hiếm) ra khỏi phòng đọc.\n"
            "2. Dịch vụ Phòng thảo luận nhóm thông minh (Group Study Rooms):\n"
            "   - Vị trí: Đặt tại Tầng 2 và Tầng 3 của Tòa nhà Thư viện, trang bị máy chiếu, bảng viết kính, điều hòa và màn hình Smart TV tương tác.\n"
            "   - Điều kiện đăng ký: Dành cho nhóm từ 3 đến 8 sinh viên/học viên có nhu cầu học tập, làm việc nhóm hoặc thuyết trình chuyên đề.\n"
            "   - Quy trình đặt phòng: Đặt lịch trực tuyến trước ít nhất 2 giờ qua cổng https://lib.qnu.edu.vn; thời gian sử dụng tối đa là 3 giờ/phiên học."
        ),
        "metadata": {
            "section": "Phần V",
            "topic": "Nội quy & Phòng thảo luận",
            "document_name": LIBRARY_FILENAME,
            "title": LIBRARY_TITLE,
            "page": 5,
        },
    },
    {
        "id": "chk_lib_6",
        "chunk_index": 5,
        "title": "Phần VI: Dịch vụ Hỗ trợ Nghiên cứu, Kiểm tra Đạo văn Turnitin và Thủ tục Thanh toán Ra trường",
        "content": (
            "Phần VI - HỖ TRỢ HỌC THUẬT VÀ THỦ TỤC THANH TOÁN THƯ VIỆN:\n"
            "1. Dịch vụ Kiểm tra tính trùng lặp học thuật (Chống đạo văn):\n"
            "   - Thư viện cung cấp tài khoản và thực hiện dịch vụ kiểm tra tỷ lệ tương đồng học thuật bằng phần mềm Turnitin dành cho sinh viên làm khóa luận tốt nghiệp, học viên cao học và giảng viên xuất bản bài báo.\n"
            "   - Hướng dẫn cài đặt và sử dụng các công cụ quản lý tài liệu trích dẫn tự động chuẩn quốc tế như Zotero, Mendeley, EndNote.\n"
            "2. Dịch vụ in ấn và số hóa học liệu theo yêu cầu:\n"
            "   - Hỗ trợ in ấn, photocopy tài liệu học tập tuân thủ đúng Luật Sở hữu trí tuệ (nghiêm cấm sao chép nhân bản nguyên cuốn sách có bản quyền thương mại).\n"
            "3. Thủ tục xác nhận thanh toán thư viện để nhận bằng tốt nghiệp ra trường:\n"
            "   - Sinh viên năm cuối phải hoàn trả toàn bộ sách đã mượn và thanh toán các khoản phí quá hạn (nếu có).\n"
            "   - Thủ tục ký xác nhận thư viện được thực hiện hoàn toàn trực tuyến tự động thông qua phần mềm quản lý; sinh viên không cần xin chữ ký giấy trực tiếp."
        ),
        "metadata": {
            "section": "Phần VI",
            "topic": "Kiểm tra đạo văn & Thanh toán ra trường",
            "document_name": LIBRARY_FILENAME,
            "title": LIBRARY_TITLE,
            "page": 6,
        },
    },
]

LIBRARY_FACTS: list[dict[str, Any]] = [
    {
        "fact_key": "fact_lib_thong_tin_chung",
        "category": "facility_profile",
        "entity_name": "Trung tâm Thông tin - Thư viện Trường Đại học Quy Nhơn",
        "attribute_name": "Vị trí, quy mô, hotline và cổng thông tin tra cứu",
        "value": (
            "Tòa nhà Thư viện 4 tầng, diện tích 4.500 m2 tại 170 An Dương Vương, Quy Nhơn. "
            "Hotline: 0256.3846.888. Email: thuvien@qnu.edu.vn. "
            "Cổng tra cứu OPAC và thư viện số: https://lib.qnu.edu.vn."
        ),
        "fact_metadata": {
            "facility_name": "Trung tâm Thông tin - Thư viện ĐH Quy Nhơn",
            "floor_count": 4,
            "floor_area_m2": 4500,
            "hotline": "0256.3846.888",
            "email": "thuvien@qnu.edu.vn",
            "website": "https://lib.qnu.edu.vn",
        },
    },
    {
        "fact_key": "fact_lib_gio_mo_cua",
        "category": "operating_hours",
        "entity_name": "Thời gian mở cửa phục vụ bạn đọc của Thư viện ĐH Quy Nhơn",
        "attribute_name": "Khung giờ phục vụ các ngày trong tuần và khu tự học",
        "value": (
            "Thứ Hai đến Thứ Bảy: Sáng từ 7h00 - 11h30, Chiều và tối từ 13h30 - 21h00. "
            "Khu tự học thông minh mở cửa phục vụ 24/7 (kể cả Chủ nhật và ngày lễ)."
        ),
        "fact_metadata": {
            "morning_open": "07:00",
            "morning_close": "11:30",
            "afternoon_open": "13:30",
            "evening_close": "21:00",
            "smart_study_zone": "24/7",
        },
    },
    {
        "fact_key": "fact_lib_han_muc_muon_sach",
        "category": "borrowing_quota",
        "entity_name": "Hạn ngạch và thời hạn mượn sách in theo từng đối tượng bạn đọc",
        "attribute_name": "Số lượng sách mượn tối đa và thời gian được giữ sách",
        "value": (
            "Sinh viên ĐH chính quy: Mượn tối đa 5 cuốn sách trong 14 ngày, gia hạn 1 lần thêm 7 ngày. "
            "Học viên Sau đại học: Tối đa 10 cuốn trong 30 ngày. "
            "Giảng viên: Tối đa 15 cuốn trong 90 ngày."
        ),
        "fact_metadata": {
            "undergraduate_max_books": 5,
            "undergraduate_days": 14,
            "postgraduate_max_books": 10,
            "postgraduate_days": 30,
            "faculty_max_books": 15,
            "faculty_days": 90,
            "renewal_times": 1,
            "renewal_days": 7,
        },
    },
    {
        "fact_key": "fact_lib_phi_phat_qua_han",
        "category": "penalty_policy",
        "entity_name": "Mức phí phạt mượn sách quá hạn và bồi thường mất sách",
        "attribute_name": "Mức phạt quá hạn hàng ngày và hình thức đền bù",
        "value": (
            "Phí phạt quá hạn mượn sách: 2.000 đồng/cuốn/ngày. "
            "Làm mất hoặc làm hỏng sách: Đền sách mới cùng loại hoặc bồi thường gấp 2 lần giá trị thị trường."
        ),
        "fact_metadata": {
            "fine_per_book_day": 2000,
            "lost_book_compensation_multiplier": 2,
        },
    },
    {
        "fact_key": "fact_lib_csdl_dien_tu",
        "category": "digital_resources",
        "entity_name": "Cơ sở dữ liệu điện tử học thuật quốc tế có bản quyền",
        "attribute_name": "Danh mục cơ sở dữ liệu và phương thức truy cập từ xa",
        "value": (
            "CSDL quốc tế có bản quyền: ScienceDirect, Scopus, IEEE Xplore, SpringerLink, ProQuest, VJOL. "
            "Truy cập trong trường qua IP nội bộ; truy cập từ xa ngoài trường qua cổng Proxy/VPN bằng tài khoản SSO @qnu.edu.vn."
        ),
        "fact_metadata": {
            "databases": ["ScienceDirect", "Scopus", "IEEE Xplore", "SpringerLink", "ProQuest", "VJOL"],
            "remote_access_protocol": "Proxy/VPN SSO",
        },
    },
    {
        "fact_key": "fact_lib_phong_hoc_nhom",
        "category": "room_booking",
        "entity_name": "Quy định đăng ký phòng thảo luận nhóm tại Thư viện",
        "attribute_name": "Quy mô nhóm, thời lượng tối đa và trang thiết bị hỗ trợ",
        "value": (
            "Phòng thảo luận nhóm tại Tầng 2 và 3 dành cho nhóm 3 - 8 người, thời lượng tối đa 3 giờ/phiên. "
            "Trang bị máy chiếu, Smart TV, bảng viết kính; đặt lịch trực tuyến trước 2 giờ qua https://lib.qnu.edu.vn."
        ),
        "fact_metadata": {
            "min_members": 3,
            "max_members": 8,
            "max_hours_per_session": 3,
            "booking_advance_hours": 2,
            "floors": [2, 3],
        },
    },
    {
        "fact_key": "fact_lib_kiem_tra_dao_van",
        "category": "academic_support",
        "entity_name": "Dịch vụ hỗ trợ kiểm tra đạo văn và trích dẫn khoa học",
        "attribute_name": "Phần mềm kiểm tra trùng lặp học thuật và công cụ trích dẫn",
        "value": (
            "Thư viện hỗ trợ kiểm tra tính trùng lặp học thuật bằng phần mềm bản quyền Turnitin "
            "cho khóa luận tốt nghiệp, luận văn thạc sĩ; hỗ trợ hướng dẫn công cụ trích dẫn Zotero, Mendeley."
        ),
        "fact_metadata": {
            "similarity_software": "Turnitin",
            "citation_tools": ["Zotero", "Mendeley", "EndNote"],
            "online_clearance": True,
        },
    },
]
