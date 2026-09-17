"""Unit tests for SmartLayoutDetector layout analysis, table containment, and signature unification."""

from __future__ import annotations

import cv2
import numpy as np
import pymupdf as fitz

from app.modules.ocr.layout_detector import SmartLayoutDetector


def test_administrative_semantics_classification():
    detector = SmartLayoutDetector()

    # Section titles
    assert detector._is_doc_or_section_title("I. MỤC ĐÍCH, YÊU CẦU") is True
    assert detector._is_doc_or_section_title("II. NỘI DUNG KẾ HOẠCH THỰC HIỆN") is True
    assert detector._is_doc_or_section_title("1.1. Mục đích") is True
    assert detector._is_doc_or_section_title("1. Trung tâm Số và Học liệu") is True
    assert detector._is_doc_or_section_title("3. Phòng Tổ chức - Nhân sự") is True
    assert detector._is_doc_or_section_title("KẾ HOẠCH\nTriển khai nâng cấp phần mềm") is True
    assert detector._is_doc_or_section_title("QUYẾT ĐỊNH\nVề việc ban hành quy chế") is True

    # Regular paragraph text (should NOT be title)
    assert detector._is_doc_or_section_title("Căn cứ Quyết định số 265/QĐ-ĐHQN ngày 15/01/2026") is False
    assert detector._is_doc_or_section_title("Nhằm triển khai chủ trương nâng cấp phần mềm Cổng thông tin") is False

    # List markers
    assert detector._is_list_marker("- Triển khai nâng cấp phần mềm Cổng thông tin") is True
    assert detector._is_list_marker("+ Gửi báo cáo định kỳ") is True
    assert detector._is_list_marker("• Hoàn thiện hồ sơ") is True
    assert detector._is_list_marker("1. Các đơn vị chủ động thực hiện") is True
    assert detector._is_list_marker("a) Đơn vị phối hợp chịu trách nhiệm") is True
    assert detector._is_list_marker("Nơi nhận:\n- Ban Giám hiệu\n- Lưu VT") is True

    # Normal text should NOT be list
    assert detector._is_list_marker("Nhà trường đề nghị các Trưởng đơn vị liên quan thực hiện nghiêm túc.") is False


def test_detect_red_stamps_adaptive_density():
    detector = SmartLayoutDetector()

    # Create synthetic image with a red circular stamp
    img = np.ones((600, 600, 3), dtype=np.uint8) * 255
    # Draw red circle (BGR: [0, 0, 220])
    cv2.circle(img, (400, 400), 50, (0, 0, 220), thickness=4)
    cv2.putText(img, "DANG UY - QNU", (370, 400), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 220), 1)

    stamps, _red_mask = detector._detect_red_stamps(img, 600, 600)
    assert len(stamps) >= 1
    stamp = stamps[0]
    assert stamp["type"] == "signature"
    assert stamp["label"] == "signature"
    assert stamp["left"] > 50.0  # right side
    assert stamp["top"] > 50.0  # lower half


def test_hybrid_pdf_layout_and_signature_unification():
    detector = SmartLayoutDetector()

    # Create a 2-page PDF document
    doc = fitz.open()

    # Page 1: Administrative header, title, and body
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text((50, 60), "TRUONG DAI HOC QUY NHON", fontsize=11)
    p1.insert_text((350, 60), "CONG HOA XA HOI CHU NGHIA VIET NAM", fontsize=11)
    p1.insert_text((200, 150), "KE HOACH\nNang cap he thong", fontsize=14)
    p1.insert_text((50, 220), "Can cu Quyet dinh so 265/QD-DHQN ngay 15 thang 01 nam 2026...", fontsize=11)
    p1.insert_text((50, 300), "I. MUC DICH, YEU CAU", fontsize=12)
    p1.insert_text((50, 340), "- Trien khai dong bo he thong tren toan truong", fontsize=11)

    # Page 2: Closing remarks, and signature block
    p2 = doc.new_page(width=595, height=842)
    p2.insert_text((50, 60), "II. NOI DUNG THUC HIEN", fontsize=12)
    p2.insert_text((50, 400), "Nha truong de nghi cac don vi thuc hien nghiem tuc.", fontsize=11)
    p2.insert_text((50, 500), "Noi nhan:\n- Cac don vi\n- Luu VT", fontsize=10)
    p2.insert_text((400, 460), "HIEU TRUONG", fontsize=12)
    p2.insert_text((380, 600), "PGS. TS. Doan Duc Tung", fontsize=12)

    # Convert page 1 to pixmap and detect
    p1_ref = doc[0]
    pix1 = p1_ref.get_pixmap(dpi=150)
    img1 = np.frombuffer(pix1.samples, dtype=np.uint8).reshape((pix1.height, pix1.width, pix1.n))
    if pix1.n >= 3:
        img1 = cv2.cvtColor(img1, cv2.COLOR_RGB2BGR)

    regions_p1 = detector.detect_layout_regions(img1, page_number=1, fitz_page=p1_ref)
    assert len(regions_p1) >= 3
    types_p1 = [r["type"] for r in regions_p1]
    assert "header" in types_p1
    assert "title" in types_p1
    assert "text" in types_p1

    # Convert page 2 to pixmap, inject synthetic red stamp between title and name, and detect
    p2_ref = doc[1]
    pix2 = p2_ref.get_pixmap(dpi=150)
    img2 = np.frombuffer(pix2.samples, dtype=np.uint8).reshape((pix2.height, pix2.width, pix2.n))
    if pix2.n >= 3:
        img2 = cv2.cvtColor(img2, cv2.COLOR_RGB2BGR)
    cv2.circle(img2, (850, 1100), 55, (0, 0, 220), thickness=4)
    cv2.putText(img2, "DAI HOC QUY NHON", (800, 1100), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 220), 1)

    regions_p2 = detector.detect_layout_regions(img2, page_number=2, fitz_page=p2_ref)
    types_p2 = [r["type"] for r in regions_p2]

    # Verify signature block is unified
    assert "signature" in types_p2
    sig_boxes = [r for r in regions_p2 if r["type"] == "signature"]
    assert len(sig_boxes) >= 1
    # Verify signature text contains title and signer
    sig_text = sig_boxes[0]["text"]
    assert "HIEU TRUONG" in sig_text
    assert "Doan Duc Tung" in sig_text

    # Verify 'Noi nhan:' is tagged as list
    list_boxes = [r for r in regions_p2 if r["type"] == "list"]
    assert len(list_boxes) >= 1
    assert "Noi nhan" in list_boxes[0]["text"]

    doc.close()


def test_list_preservation_and_table_separation():
    """Verify that itemized lists (b., c., a), b)) and tables are preserved as distinct entities."""
    detector = SmartLayoutDetector()
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    # 1. Lead text
    page.insert_text((50, 60), "Truong hop nhieu thi sinh co cung diem xet o cuoi danh sach.", fontsize=11)
    # 2. List items b. and c.
    page.insert_text((50, 100), "b. Diem cong: xem chi tiet tai Muc 7;", fontsize=11)
    page.insert_text((50, 120), "c. Su dung chung chi VSTEP, IELTS thay cho diem tieng Anh:", fontsize=11)

    # 3. Simple Table grid with 2 columns
    page.draw_rect(fitz.Rect(50, 150, 300, 250))
    page.draw_line(fitz.Point(50, 200), fitz.Point(300, 200))
    page.draw_line(fitz.Point(175, 150), fitz.Point(175, 250))
    page.insert_text((60, 180), "IELTS", fontsize=10)
    page.insert_text((190, 180), "Quy doi", fontsize=10)
    page.insert_text((60, 230), "6.0", fontsize=10)
    page.insert_text((190, 230), "9.0", fontsize=10)

    # 4. Intermediate text
    page.insert_text((50, 290), "Thi sinh nop chung chi tai cac diem tiep nhan de nhap len co so du lieu.", fontsize=11)

    # 5. List items a), b), c)
    page.insert_text((50, 330), "a) Thi sinh nop ho so xet tuyen thang tu ngay 20/5/2026.", fontsize=11)
    page.insert_text((50, 350), "b) Thi nang khieu vao ngay 19, 20/6/2026.", fontsize=11)
    page.insert_text((50, 370), "c) Xet tuyen dot 1 tren he thong cua Bo tu ngay 02/7/2026.", fontsize=11)

    # 6. Closing text
    page.insert_text((50, 420), "Cong bo nguong bao dam chat luong dau vao theo quy dinh cua Bo.", fontsize=11)

    pix = page.get_pixmap(dpi=150)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
    if pix.n >= 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    regions = detector.detect_layout_regions(img, page_number=9, fitz_page=page)
    types = [r["type"] for r in regions]

    # Verify both 'list', 'table', and 'text' are recognized
    assert "table" in types
    assert "list" in types
    assert "text" in types

    list_boxes = [r for r in regions if r["type"] == "list"]
    assert len(list_boxes) >= 2, f"Expected at least 2 list blocks, got {len(list_boxes)}"
    # First list contains b. and c.
    assert any("b. Diem cong" in r["text"] for r in list_boxes)
    # Second list contains a), b), c)
    assert any("a) Thi sinh" in r["text"] for r in list_boxes)

    doc.close()

