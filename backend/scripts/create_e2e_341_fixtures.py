"""Create synthetic, clearly labelled fixtures for the post-fix browser E2E."""

from pathlib import Path

import fitz


def main() -> None:
    target = Path(__file__).resolve().parents[1] / "storage" / "e2e_fixtures" / "341"
    target.mkdir(parents=True, exist_ok=True)
    native = fitz.open()
    texts = [
        (
            "TÀI LIỆU KIỂM THỬ E2E 341 - KHÔNG PHẢI VĂN BẢN CHÍNH THỨC\n\n"
            "Trang 1: Giới thiệu bộ dữ liệu tổng hợp dùng kiểm tra luồng lưu trữ và OCR.\n\n"
            "Mã kiểm chứng: E2E341-PAGE1. Thông số kiểm thử nằm riêng ở trang 2."
        ),
        (
            "TÀI LIỆU KIỂM THỬ E2E 341 - TRANG 2\n\n"
            "Điều 2. Trong bộ dữ liệu tổng hợp E2E341-PAGE2, học phí ngành Công nghệ thông tin "
            "là 21.341.000 đồng mỗi năm. Đây là số liệu giả định chỉ dùng kiểm thử, "
            "không phải học phí thực tế của Trường Đại học Quy Nhơn.\n\n"
            "Mã kiểm chứng: E2E341-PAGE2. Chỉ tiêu giả định là 137 sinh viên."
        ),
    ]
    scan = fitz.open()
    for idx, text in enumerate(texts):
        page = native.new_page()
        page.insert_font(fontname="fixture", fontfile="C:/Windows/Fonts/arial.ttf")
        remaining = page.insert_textbox(
            fitz.Rect(50, 60, 545, 770), text, fontname="fixture", fontsize=16
        )
        assert remaining > 0, "Fixture text overflow"
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        pixmap.save(target / f"scan_page_{idx + 1}.png")
        scanned_page = scan.new_page(width=page.rect.width, height=page.rect.height)
        scanned_page.insert_image(scanned_page.rect, stream=pixmap.tobytes("png"))
    native.save(target / "e2e341_native_2pages.pdf")
    scan.save(target / "e2e341_scan_2pages.pdf")
    assert all(not p.get_text().strip() for p in scan)
    native.close()
    scan.close()
    (target / "e2e341_corrupt.pdf").write_bytes(b"%PDF-1.7\nE2E341 invalid PDF test fixture")
    print(target)


if __name__ == "__main__":
    main()
