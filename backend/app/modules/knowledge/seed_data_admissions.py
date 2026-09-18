"""Seed data for official QNU Admissions Knowledge (Thông báo & Đề án Tuyển sinh ĐH Quy Nhơn)."""

from __future__ import annotations

from typing import Any

ADMISSIONS_DOCUMENT_ID = "doc_qnu_tuyen_sinh_2024"
ADMISSIONS_COLLECTION_ID = "col_admissions"
ADMISSIONS_TITLE = "Thông báo tuyển sinh đại học chính quy Trường Đại học Quy Nhơn năm 2024"
ADMISSIONS_FILENAME = "Thong_bao_tuyen_sinh_DH_chinh_quy_QNU_2024.pdf"

ADMISSIONS_CHUNKS: list[dict[str, Any]] = [
    {
        "id": "chk_adm_1",
        "chunk_index": 0,
        "title": "Phần I: Thông tin chung & Cơ sở đào tạo (Mã trường, Hotline, Địa chỉ)",
        "content": (
            "TRƯỜNG ĐẠI HỌC QUY NHƠN — THÔNG BÁO TUYỂN SINH ĐẠI HỌC CHÍNH QUY NĂM 2024\n"
            "Phần I - THÔNG TIN CHUNG VÀ CƠ SỞ ĐÀO TẠO:\n"
            "1. Tên cơ sở đào tạo: Trường Đại học Quy Nhơn (Quy Nhon University - QNU).\n"
            "2. Mã cơ sở đào tạo (Mã trường) dùng trong tuyển sinh toàn quốc: DQN.\n"
            "3. Địa chỉ trụ sở chính: Số 170 An Dương Vương, phường Nguyễn Văn Cừ, thành phố Quy Nhơn, tỉnh Bình Định.\n"
            "4. Điện thoại hotline tư vấn tuyển sinh chính thức: 0256.3846.156 hoặc đường dây nóng miễn cước 1800.55.88.49.\n"
            "5. Email tiếp nhận giải đáp thắc mắc tuyển sinh: tuyensinh@qnu.edu.vn.\n"
            "6. Cổng thông tin tuyển sinh điện tử chính thức: https://qnu.edu.vn và https://tuyensinh.qnu.edu.vn.\n"
            "7. Fanpage tuyển sinh chính thức: https://facebook.com/qnu.edu.vn."
        ),
        "metadata": {
            "section": "Phần I",
            "topic": "Thông tin chung & Liên hệ",
            "document_name": ADMISSIONS_FILENAME,
            "title": ADMISSIONS_TITLE,
            "page": 1,
        },
    },
    {
        "id": "chk_adm_2",
        "chunk_index": 1,
        "title": "Phần II: 4 Phương thức xét tuyển đại học chính quy năm 2024",
        "content": (
            "Phần II - CÁC PHƯƠNG THỨC XÉT TUYỂN ĐẠI HỌC CHÍNH QUY:\n"
            "Trường Đại học Quy Nhơn áp dụng 4 phương thức xét tuyển độc lập cho 53 ngành đào tạo đại học chính quy:\n"
            "1. Phương thức 1 (Mã 100): Xét tuyển dựa vào kết quả kỳ thi tốt nghiệp THPT năm 2024 theo các tổ hợp môn tương ứng từng ngành.\n"
            "2. Phương thức 2 (Mã 200): Xét tuyển dựa vào kết quả học tập THPT (Xét học bạ THPT):\n"
            "   - Tiêu chí: Tổng điểm trung bình 3 môn theo tổ hợp xét tuyển của cả năm lớp 12 đạt từ 18.00 điểm trở lên (đối với khối ngành ngoài Sư phạm).\n"
            "   - Đối với khối ngành đào tạo giáo viên (Sư phạm): Học lực lớp 12 xếp loại Giỏi hoặc điểm xét tốt nghiệp THPT từ 8.0 trở lên, tổng điểm 3 môn từ 24.00 điểm trở lên.\n"
            "3. Phương thức 3 (Mã 402): Xét tuyển dựa vào kết quả kỳ thi Đánh giá năng lực do Đại học Quốc gia TP.HCM tổ chức năm 2024:\n"
            "   - Ngưỡng điểm nhận hồ sơ xét tuyển: Đạt từ 600 đến 750 điểm trở lên (trên thang điểm 1.200) tùy theo từng ngành.\n"
            "4. Phương thức 4 (Mã 301): Xét tuyển thẳng và ưu tiên xét tuyển theo Quy chế tuyển sinh của Bộ GD&ĐT (thí sinh đạt giải học sinh giỏi quốc gia, quốc tế, cuộc thi KHKT quốc gia)."
        ),
        "metadata": {
            "section": "Phần II",
            "topic": "Phương thức xét tuyển",
            "document_name": ADMISSIONS_FILENAME,
            "title": ADMISSIONS_TITLE,
            "page": 2,
        },
    },
    {
        "id": "chk_adm_3",
        "chunk_index": 2,
        "title": "Phần III: Khối ngành Sư phạm & Chính sách hỗ trợ sinh hoạt phí theo Nghị định 116",
        "content": (
            "Phần III - KHỐI NGÀNH ĐÀO TẠO GIÁO VIÊN (SƯ PHẠM) VÀ NGHỊ ĐỊNH 116:\n"
            "1. Các ngành đào tạo giáo viên trọng điểm: Sư phạm Toán học, Sư phạm Tin học, Sư phạm Vật lý, Sư phạm Hóa học, "
            "Sư phạm Ngữ văn, Sư phạm Lịch sử, Sư phạm Tiếng Anh, Giáo dục Tiểu học, Giáo dục Mầm non.\n"
            "2. Chính sách ưu đãi đặc biệt theo Nghị định số 116/2020/NĐ-CP của Chính phủ:\n"
            "   - Sinh viên sư phạm theo học tại Trường Đại học Quy Nhơn được Nhà nước hỗ trợ 100% tiền đóng học phí trong suốt 4 năm học.\n"
            "   - Được chi trả trợ cấp sinh hoạt phí hàng tháng là 3,63 triệu đồng/tháng (3.630.000 đ/tháng), chi trả 10 tháng/năm học để trang trải chi phí ăn ở, học tập.\n"
            "3. Điểm chuẩn trúng tuyển tiêu biểu khối Sư phạm năm gần nhất:\n"
            "   - Sư phạm Toán học: 26.25 điểm (Tổ hợp A00, A01).\n"
            "   - Giáo dục Tiểu học: 25.50 điểm (Tổ hợp C00, D01).\n"
            "   - Sư phạm Tiếng Anh: 25.75 điểm (Tiếng Anh nhân hệ số 2)."
        ),
        "metadata": {
            "section": "Phần III",
            "topic": "Khối ngành Sư phạm & Nghị định 116",
            "document_name": ADMISSIONS_FILENAME,
            "title": ADMISSIONS_TITLE,
            "page": 3,
        },
    },
    {
        "id": "chk_adm_4",
        "chunk_index": 3,
        "title": "Phần IV: Khối ngành Công nghệ Thông tin & Kỹ thuật — Công nghệ",
        "content": (
            "Phần IV - KHỐI NGÀNH CÔNG NGHỆ THÔNG TIN VÀ KỸ THUẬT:\n"
            "1. Ngành Công nghệ thông tin (Mã ngành: 7480201):\n"
            "   - Các tổ hợp môn xét tuyển: A00 (Toán, Lý, Hóa), A01 (Toán, Lý, Tiếng Anh), D01 (Toán, Ngữ văn, Tiếng Anh), D07 (Toán, Hóa học, Tiếng Anh).\n"
            "   - Điểm chuẩn trúng tuyển năm gần nhất: 24.50 điểm.\n"
            "   - Định hướng chuyên sâu: Trí tuệ nhân tạo (AI), Kỹ thuật dữ liệu (Data Engineering), Phát triển phần mềm Web/Mobile, An toàn thông tin.\n"
            "2. Ngành Kỹ thuật phần mềm (Mã ngành: 7480103):\n"
            "   - Xét tuyển các tổ hợp: A00, A01, D01, D07. Điểm chuẩn: 23.00 điểm.\n"
            "3. Cơ hội nghề nghiệp và đối tác chiến lược:\n"
            "   - Sinh viên được thực tập và cam kết việc làm tại Công viên phần mềm Quang Trung - Bình Định, Tập đoàn FPT Software, TMA Solutions, Axon Active, Enclave ngay từ năm thứ 3 và năm thứ 4."
        ),
        "metadata": {
            "section": "Phần IV",
            "topic": "Khối ngành CNTT & Kỹ thuật",
            "document_name": ADMISSIONS_FILENAME,
            "title": ADMISSIONS_TITLE,
            "page": 4,
        },
    },
    {
        "id": "chk_adm_5",
        "chunk_index": 4,
        "title": "Phần V: Khối ngành Kinh tế, Ngôn ngữ, Du lịch & Khoa học Xã hội",
        "content": (
            "Phần V - KHỐI NGÀNH KINH TẾ, DU LỊCH VÀ NGÔN NGỮ:\n"
            "1. Các ngành tuyển sinh nổi bật:\n"
            "   - Quản trị kinh doanh (Mã 7340101): Điểm chuẩn 21.50 điểm (Tổ hợp A00, A01, D01, D07).\n"
            "   - Kinh tế quốc tế (Mã 7310106): Điểm chuẩn 21.00 điểm (Tổ hợp A00, A01, D01, D07).\n"
            "   - Tài chính - Ngân hàng (Mã 7340201): Điểm chuẩn 20.50 điểm.\n"
            "   - Quản trị dịch vụ du lịch và lữ hành (Mã 7810103): Điểm chuẩn 20.00 điểm.\n"
            "   - Ngôn ngữ Anh (Mã 7220201): Điểm chuẩn 22.50 điểm (Tiếng Anh nhân hệ số 2, tổ hợp D01, D14, D15).\n"
            "2. Môi trường đào tạo:\n"
            "   - Thành phố Quy Nhơn là trung tâm du lịch biển trọng điểm quốc gia, tạo cơ hội thực tập nghề nghiệp phong phú tại các tập đoàn khách sạn resort 5 sao (FLC, TMS, Maia Resort) và ngân hàng lớn (Vietcombank, BIDV, Agribank)."
        ),
        "metadata": {
            "section": "Phần V",
            "topic": "Khối ngành Kinh tế & Du lịch",
            "document_name": ADMISSIONS_FILENAME,
            "title": ADMISSIONS_TITLE,
            "page": 5,
        },
    },
    {
        "id": "chk_adm_6",
        "chunk_index": 5,
        "title": "Phần VI: Học phí theo tín chỉ & Chính sách Học bổng tài trợ sinh viên",
        "content": (
            "Phần VI - MỨC HỌC PHÍ VÀ CHÍNH SÁCH HỌC BỔNG:\n"
            "1. Mức học phí (thu theo số tín chỉ thực tế sinh viên đăng ký học):\n"
            "   - Khối ngành Khoa học xã hội, Kinh tế, Luật, Du lịch: Khoảng 14.500.000 - 17.500.000 đ/năm học (tương đương 450.000 - 550.000 đ/tín chỉ).\n"
            "   - Khối ngành Khoa học tự nhiên, Công nghệ thông tin, Kỹ thuật, Nông nghiệp: Khoảng 18.000.000 - 22.000.000 đ/năm học (tương đương 550.000 - 680.000 đ/tín chỉ).\n"
            "   - Khối ngành Sư phạm: Miễn 100% học phí theo Nghị định 116/2020/NĐ-CP.\n"
            "2. Quỹ học bổng khuyến khích học tập:\n"
            "   - Học bổng loại Xuất sắc: 120% mức học phí của học kỳ tương ứng.\n"
            "   - Học bổng loại Giỏi: 100% mức học phí của học kỳ tương ứng.\n"
            "   - Học bổng loại Khá: 80% mức học phí của học kỳ tương ứng.\n"
            "   - Học bổng Vallet (Pháp) dành cho sinh viên xuất sắc: 20 triệu đồng/suất; học bổng doanh nghiệp (FPT, TMA, Vietcombank) tài trợ hàng năm trên 5 tỷ đồng."
        ),
        "metadata": {
            "section": "Phần VI",
            "topic": "Học phí & Học bổng",
            "document_name": ADMISSIONS_FILENAME,
            "title": ADMISSIONS_TITLE,
            "page": 6,
        },
    },
    {
        "id": "chk_adm_7",
        "chunk_index": 6,
        "title": "Phần VII: Ký túc xá sinh viên, Điều kiện sinh hoạt & Thủ tục nhập học",
        "content": (
            "Phần VII - KÝ TÚC XÁ, ĐIỀU KIỆN ĂN Ở VÀ QUY TRÌNH NHẬP HỌC:\n"
            "1. Ký túc xá Trường Đại học Quy Nhơn:\n"
            "   - Vị trí: Nằm ngay trong khuôn viên trường, sát biển Quy Nhơn thoáng mát, an ninh trật tự 24/7.\n"
            "   - Quy mô: Sức chứa trên 5.000 chỗ ở nội trú cho tân sinh viên và sinh viên các khóa.\n"
            "   - Chi phí lưu trú: Rất tiết kiệm, chỉ từ 150.000 đến 300.000 đồng/tháng/sinh viên (đã bao gồm tiện ích mạng wifi internet tốc độ cao).\n"
            "   - Tiện ích phụ trợ: Nhà ăn sinh viên, căng tin, thư viện 4 tầng hiện đại, sân bóng đá cỏ nhân tạo, sân tennis, nhà thi đấu đa năng.\n"
            "2. Quy trình xác nhận nhập học:\n"
            "   - Bước 1: Thí sinh xác nhận nhập học trực tuyến trên Cổng thông tin của Bộ GD&ĐT (http://thisinh.thitotnghiepthpt.edu.vn).\n"
            "   - Bước 2: Thực hiện thủ tục nhập học trực tuyến trên cổng https://nhaphoc.qnu.edu.vn và nhận giấy báo trúng tuyển bản chính tại Trường."
        ),
        "metadata": {
            "section": "Phần VII",
            "topic": "Ký túc xá & Nhập học",
            "document_name": ADMISSIONS_FILENAME,
            "title": ADMISSIONS_TITLE,
            "page": 7,
        },
    },
]

ADMISSIONS_FACTS: list[dict[str, Any]] = [
    {
        "fact_key": "fact_adm_thong_tin_chung",
        "category": "institution_profile",
        "entity_name": "Thông tin pháp lý & Liên hệ tuyển sinh Trường ĐH Quy Nhơn",
        "attribute_name": "Mã trường, hotline, địa chỉ cơ sở đào tạo",
        "value": (
            "Mã cơ sở đào tạo: DQN. Trụ sở: 170 An Dương Vương, Quy Nhơn, Bình Định. "
            "Hotline tư vấn: 0256.3846.156 hoặc 1800.55.88.49. Website: https://qnu.edu.vn. "
            "Email: tuyensinh@qnu.edu.vn."
        ),
        "fact_metadata": {
            "institution_code": "DQN",
            "hotline": "0256.3846.156",
            "toll_free": "1800.55.88.49",
            "address": "170 An Dương Vương, Quy Nhơn, Bình Định",
            "website": "https://qnu.edu.vn",
        },
    },
    {
        "fact_key": "fact_adm_phuong_thuc_xet_tuyen",
        "category": "admission_methods",
        "entity_name": "4 Phương thức tuyển sinh đại học chính quy ĐH Quy Nhơn",
        "attribute_name": "Danh mục phương thức xét tuyển và điều kiện sàn",
        "value": (
            "PT1: Điểm thi tốt nghiệp THPT năm 2024; "
            "PT2: Xét học bạ THPT lớp 12 (Tổng 3 môn >= 18.00 đ; khối Sư phạm >= 24.00 đ và học lực Giỏi); "
            "PT3: Điểm thi ĐGNL ĐHQG-HCM năm 2024 (Đạt từ 600 - 750 điểm trở lên); "
            "PT4: Tuyển thẳng theo quy chế Bộ GD&ĐT."
        ),
        "fact_metadata": {
            "method_count": 4,
            "min_transcript_score": 18.00,
            "min_pedagogy_transcript_score": 24.00,
            "min_dgnl_score": 600,
        },
    },
    {
        "fact_key": "fact_adm_chi_tieu_tong",
        "category": "admission_quota",
        "entity_name": "Chỉ tiêu tuyển sinh đại học chính quy ĐH Quy Nhơn",
        "attribute_name": "Tổng chỉ tiêu tuyển sinh toàn trường năm 2024",
        "value": "Tổng chỉ tiêu tuyển sinh đại học chính quy năm 2024 là 5.860 chỉ tiêu cho 53 ngành đào tạo.",
        "fact_metadata": {
            "total_quota": 5860,
            "major_count": 53,
            "year": 2024,
        },
    },
    {
        "fact_key": "fact_adm_diem_chuan_cntt",
        "category": "cutoff_score",
        "entity_name": "Điểm chuẩn ngành Công nghệ thông tin ĐH Quy Nhơn",
        "attribute_name": "Điểm chuẩn trúng tuyển và tổ hợp môn xét tuyển",
        "value": (
            "Ngành Công nghệ thông tin (mã ngành 7480201) có điểm chuẩn trúng tuyển là 24.50 điểm. "
            "Các tổ hợp môn xét tuyển: A00 (Toán, Lý, Hóa), A01 (Toán, Lý, Tiếng Anh), "
            "D01 (Toán, Ngữ văn, Tiếng Anh), D07 (Toán, Hóa học, Tiếng Anh)."
        ),
        "fact_metadata": {
            "major_code": "7480201",
            "major_name": "Công nghệ thông tin",
            "cutoff_score": 24.50,
            "subject_groups": ["A00", "A01", "D01", "D07"],
        },
    },
    {
        "fact_key": "fact_adm_diem_chuan_sp_toan",
        "category": "cutoff_score",
        "entity_name": "Điểm chuẩn ngành Sư phạm Toán học ĐH Quy Nhơn",
        "attribute_name": "Điểm chuẩn trúng tuyển và tổ hợp môn xét tuyển",
        "value": (
            "Ngành Sư phạm Toán học (mã ngành 7140209) có điểm chuẩn trúng tuyển là 26.25 điểm. "
            "Các tổ hợp môn xét tuyển: A00 (Toán, Lý, Hóa), A01 (Toán, Lý, Tiếng Anh)."
        ),
        "fact_metadata": {
            "major_code": "7140209",
            "major_name": "Sư phạm Toán học",
            "cutoff_score": 26.25,
            "subject_groups": ["A00", "A01"],
        },
    },
    {
        "fact_key": "fact_adm_hoc_phi_khoi_nganh",
        "category": "tuition_fee",
        "entity_name": "Khung học phí đại học chính quy ĐH Quy Nhơn theo năm học",
        "attribute_name": "Mức học phí theo từng khối ngành đào tạo",
        "value": (
            "Khối Kinh tế, Xã hội, Luật: 14.500.000 - 17.500.000 đ/năm (450.000 - 550.000 đ/tín chỉ). "
            "Khối Tự nhiên, CNTT, Kỹ thuật: 18.000.000 - 22.000.000 đ/năm (550.000 - 680.000 đ/tín chỉ). "
            "Khối ngành Sư phạm: Miễn 100% học phí theo Nghị định 116."
        ),
        "fact_metadata": {
            "tuition_social_min": 14500000,
            "tuition_social_max": 17500000,
            "tuition_stem_min": 18000000,
            "tuition_stem_max": 22000000,
        },
    },
    {
        "fact_key": "fact_adm_chinh_sach_nd116",
        "category": "pedagogy_support",
        "entity_name": "Chính sách hỗ trợ sinh viên sư phạm theo Nghị định 116/2020/NĐ-CP",
        "attribute_name": "Quyền lợi hỗ trợ học phí và sinh hoạt phí",
        "value": (
            "Sinh viên các ngành đào tạo giáo viên (Sư phạm) tại ĐH Quy Nhơn được Nhà nước: "
            "1. Miễn 100% tiền học phí trong suốt 4 năm học; "
            "2. Hỗ trợ chi phí sinh hoạt 3,63 triệu đồng/tháng (chi trả 10 tháng/năm học)."
        ),
        "fact_metadata": {
            "decree": "116/2020/NĐ-CP",
            "tuition_free": True,
            "monthly_allowance": 3630000,
            "months_per_year": 10,
        },
    },
    {
        "fact_key": "fact_adm_ky_tuc_xa",
        "category": "dormitory",
        "entity_name": "Ký túc xá sinh viên Trường Đại học Quy Nhơn",
        "attribute_name": "Sức chứa, vị trí và mức phí lưu trú ký túc xá",
        "value": (
            "Sức chứa trên 5.000 chỗ ở nội trú, vị trí sát biển trong khuôn viên trường. "
            "Chi phí lưu trú: 150.000 - 300.000 đồng/tháng/sinh viên (đã có wifi miễn phí)."
        ),
        "fact_metadata": {
            "capacity": 5000,
            "price_min": 150000,
            "price_max": 300000,
            "has_wifi": True,
        },
    },
]
