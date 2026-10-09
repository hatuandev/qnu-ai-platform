import re

text = """**3. Thủ tục dự tuyển**

Thí sinh nộp 01 bộ hồ sơ giấy về Trường Đại học Quy Nhơn theo địa chỉ: *Phòng Đào tạo – Trường Đại học Quy Nhơn, Số 170 An Dương Vương, P. Quy Nhơn Nam, tỉnh Gia Lai.*

Hồ sơ gồm có:
* Phiếu đăng ký xét tuyển;
* Đối với người có trình độ trung cấp: nộp bằng tốt nghiệp trung cấp kèm theo bằng tốt nghiệp trung học phổ thông hoặc Giấy chứng nhận hoàn thành chương trình giáo dục phổ thông theo quy định có chứng thực.
* Đối với người có trình độ cao đẳng hoặc đại học: nộp bằng tốt nghiệp cao đẳng hoặc đại học tương ứng có chứng thực.
* Bản sao có chứng thực bảng điểm trung cấp/cao đẳng/đại học;
* 04 ảnh màu cỡ 3 × 4 cm;

Thời gian nhận hồ sơ:
* Đợt 1: từ ngày 07/7/2025 đến hết ngày 15/8/2025
* Đợt 2: từ ngày 16/8/2025 đến hết ngày 15/9/2025
* Đợt 3: từ ngày 16/09/2025 đến hết ngày 30/11/2025

**4. Thời gian đào tạo, hình thức học và chuẩn đầu ra**

Thời gian đào tạo được xác định dựa trên trình độ đầu vào của thí sinh. Cụ thể: thí sinh đã tốt nghiệp trung cấp học 5 - 6 kỳ; thí sinh có bằng cao đẳng học 4 kỳ; đối với thí sinh đã có bằng đại học học 4 - 5 kỳ.

Hình thức học: trực tuyến

Thời gian học: linh hoạt, phù hợp với người đi làm – chủ yếu vào buổi tối các ngày trong tuần hoặc cuối tuần (Thứ Bảy, Chủ Nhật).

Chuẩn đầu ra: Đạt chuẩn đầu ra chương trình đào tạo và năng lực ngoại ngữ, ứng dụng công nghệ thông tin cơ bản theo chuẩn quy định tại Quyết định số 1873/QĐ-ĐHQN ngày 30/6/2025 của Trường Đại học Quy Nhơn.

**5. Phí tuyển sinh**

Phí tuyển sinh: 400.000 đồng/thí sinh.

Hội đồng tuyển sinh Trường Đại học Quy Nhơn trân trọng thông báo để các thí sinh biết và thực hiện./."""

raw_paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
expanded = []
for p in raw_paragraphs:
    lines = [ln.strip() for ln in p.splitlines() if ln.strip()]
    if any(re.match(r"^[\*\-\+•]\s+", ln) for ln in lines):
        curr_intro = []
        for ln in lines:
            if re.match(r"^[\*\-\+•]\s+", ln):
                if curr_intro:
                    expanded.append("\n".join(curr_intro))
                    curr_intro = []
                expanded.append(ln)
            else:
                curr_intro.append(ln)
        if curr_intro:
            expanded.append("\n".join(curr_intro))
    else:
        expanded.append(p)

print(f"Total expanded items: {len(expanded)}")
for i, item in enumerate(expanded, 1):
    print(f"  [{i:2d}] {item[:40]!r}")
