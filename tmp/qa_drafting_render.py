import asyncio
from pathlib import Path

from docx import Document

from app.modules.tools.document_generator import (
    convert_docx_to_pdf_gotenberg,
    render_docx_template,
)


output_path = Path("../tmp/drafting-document-qa.docx").resolve()
docx_bytes = render_docx_template(
        "to_trinh",
        {
            "is_draft": True,
            "so_hieu": "[CHƯA CẤP SỐ]/TTr-ĐHQN",
            "ngay": "27",
            "thang": "9",
            "nam": "2026",
            "don_vi_ban_hanh": "TRƯỜNG ĐẠI HỌC QUY NHƠN",
            "kinh_gui": "Ban Giám hiệu Trường Đại học Quy Nhơn",
            "trich_yeu": "Tổ chức sự kiện Ấn tượng QNU",
            "noi_dung": (
                "Kính trình Ban Giám hiệu xem xét chủ trương tổ chức sự kiện "
                "Ấn tượng QNU tại Trường Đại học Quy Nhơn.\n\n"
                "Thời gian tổ chức: [BỔ SUNG].\n"
                "Địa điểm: [BỔ SUNG].\n"
                "Đơn vị chủ trì: [BỔ SUNG]."
            ),
            "noi_nhan": "- Ban Giám hiệu;\n- Lưu: VT.",
            "chuc_vu_nguoi_ky": "[BỔ SUNG CHỨC VỤ NGƯỜI KÝ]",
            "ho_ten_nguoi_ky": "[BỔ SUNG HỌ TÊN NGƯỜI KÝ]",
        },
    )
output_path.write_bytes(docx_bytes)

text = "\n".join(paragraph.text for paragraph in Document(output_path).paragraphs)
unresolved = "{{" in text or "}}" in text
print(f"output={output_path}")
print(f"unresolved_template_tokens={unresolved}")
print(f"has_draft_notice={'DỰ THẢO — CHƯA BAN HÀNH' in text}")
print(f"has_subject={'Tổ chức sự kiện Ấn tượng QNU' in text}")

pdf_bytes = asyncio.run(convert_docx_to_pdf_gotenberg(docx_bytes, output_path.name))
if pdf_bytes:
    pdf_path = output_path.with_suffix(".pdf")
    pdf_path.write_bytes(pdf_bytes)
    print(f"pdf={pdf_path}")
else:
    print("pdf=unavailable")
