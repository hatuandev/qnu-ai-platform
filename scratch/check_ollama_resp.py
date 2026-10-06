import asyncio
import os
import sys
import time
import base64
import json
import pymupdf as fitz
import httpx

sys.path.insert(0, os.path.abspath("backend"))

from app.modules.ocr.adapters.openai_vision_adapter import QwenOCRAdapter

async def main():
    pdf_path = r"D:\DuAnPhanMem\qnu-ai-platform\docs\tai_lieu\tuyen_sinh\vua_lam_vua_hoc\QD2139_Muc_thu_hoc_phi_dao_tao_dai_hoc_tu_xa_dot_1.pdf"
    with open(pdf_path, "rb") as f:
        content = f.read()

    adapter = QwenOCRAdapter(model_name="qwen3-vl:8b")

    # Render page 1
    doc = fitz.open(stream=content, filetype="pdf")
    page1 = doc[0]
    pix = page1.get_pixmap(dpi=150)
    img_bytes = pix.tobytes("jpeg")
    doc.close()

    b64 = base64.b64encode(img_bytes).decode("utf-8")

    prompt = (
        f"Bạn là chuyên gia OCR và phân tích cấu trúc tài liệu hành chính tiếng Việt cao cấp "
        f"của Trường Đại học Quy Nhơn (QNU). Hãy bóc tách nội dung Trang 1 của tài liệu này.\n"
        "Quy tắc bắt buộc:\n"
        "1. BẢO TOÀN NỘI DUNG & CHÍNH TẢ: Giữ nguyên 100% nội dung chữ, tiêu đề cấp mục (#, ##, ###), "
        "số hiệu văn bản, ngày tháng, họ tên, các điều khoản, ghi chú, con dấu và chữ ký. Nhận diện chuẩn xác "
        "thuật ngữ hành chính và tài chính.\n"
        "2. CẤM TUYỆT ĐỐI THẺ HTML THÔ (ZERO RAW HTML TAGS): Tuyệt đối KHÔNG sử dụng các thẻ HTML như "
        "<table>, <tr>, <td>, <hr>, <br>, <center>, <b>, <i> để dàn trang. 100% sử dụng Markdown GFM thuần khiết. "
        "Các khối Quốc hiệu, tiêu ngữ, số hiệu văn bản và Nơi nhận, người ký phải viết dưới dạng văn bản Markdown chuẩn (**, *, -).\n"
        "3. BẢNG BIỂU CHUẨN GFM & PHẲNG HÓA DỮ LIỆU: Mọi bảng biểu phải chuyển thành bảng Markdown hoàn chỉnh với hàng tiêu đề "
        "và hàng phân cách '|:---|:---|'. Giữ nguyên vẹn toàn bộ các hàng và cột.\n"
        "   - BẢNG HỌC PHÍ / CHỈ TIÊU: Mỗi phương án đào tạo (thời gian học, mức học phí) tách thành 1 HÀNG ĐỘC LẬP đầy đủ thông tin. "
        "TUYỆT ĐỐI KHÔNG gộp nhiều mức học phí vào cùng một ô bằng thẻ <br> hay dấu xuống dòng.\n"
        "   - BẢNG TIẾP NỐI QUA TRANG: Giữ lại đầy đủ 100% các hàng tiếp nối ở đầu trang (kể cả hàng có STT bị để trống). Lặp lại hàng tiêu đề bảng.\n"
        "4. CHỐNG BẺ ĐÔI TỪ: Không bẻ gãy từ tiếng Việt.\n"
        "5. CHUẨN UTF-8: Đảm bảo toàn bộ ký tự tiếng Việt hiển thị sạch sẽ theo chuẩn Unicode NFC.\n"
        "6. KHUNG TỌA ĐỘ BỐ CỤC (BOUNDING BOXES): Tại đầu trang, chèn một khối ```layout_json "
        "chứa danh sách các khối trên trang với tọa độ chuẩn hóa box_2d [ymin, xmin, ymax, xmax] (thang đo 0 đến 1000):\n"
        "   - 'header': Quốc hiệu, tiêu ngữ, tên cơ quan, số hiệu văn bản (đỉnh trang).\n"
        "   - 'title': Tiêu đề văn bản (THÔNG BÁO, QUYẾT ĐỊNH, QUY ĐỊNH...).\n"
        "   - 'table': Vùng bao quanh toàn bộ bảng số liệu.\n"
        "   - 'list': Danh sách gạch đầu dòng, danh sách hồ sơ, Nơi nhận...\n"
        "   - 'text': Các đoạn văn bản thông thường, căn cứ pháp lý.\n"
        "   - 'signature': Vùng con dấu đỏ và chữ ký của lãnh đạo.\n"
        "Ví dụ mẫu đầu trang:\n"
        "```layout_json\n"
        "[\n"
        "  {\"label\": \"header\", \"box_2d\": [40, 80, 160, 920], \"snippet\": \"BỘ GIÁO DỤC...\"},\n"
        "  {\"label\": \"title\", \"box_2d\": [180, 180, 240, 820], \"snippet\": \"THÔNG BÁO...\"},\n"
        "  {\"label\": \"table\", \"box_2d\": [320, 80, 480, 920], \"snippet\": \"STT | Mã ngành...\"}\n"
        "]\n"
        "```\n"
        "[Tiếp theo là toàn bộ nội dung Markdown chi tiết của trang]\n"
    )

    payload = {
        "model": "qwen3-vl:8b",
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [b64],
            }
        ],
        "options": {
            "temperature": 0.1,
            "num_predict": 8192,
        },
        "stream": False,
    }

    t0 = time.time()
    async with httpx.AsyncClient(timeout=180.0, trust_env=False) as client:
        resp = await client.post(f"{adapter._base_url}/api/chat", json=payload)
    
    dur = time.time() - t0
    data = resp.json()

    with open("scratch/full_ollama_resp.json", "w", encoding="utf-8") as f:
        # Don't dump full if huge, but let's see keys and message
        json.dump({
            "status_code": resp.status_code,
            "duration_s": dur,
            "keys": list(data.keys()),
            "message_keys": list(data.get("message", {}).keys()),
            "message_role": data.get("message", {}).get("role"),
            "content_len": len(data.get("message", {}).get("content", "")),
            "content": data.get("message", {}).get("content", ""),
            "thinking": data.get("message", {}).get("thinking", "") if "thinking" in data.get("message", {}) else None,
            "done_reason": data.get("done_reason"),
            "eval_count": data.get("eval_count"),
            "prompt_eval_count": data.get("prompt_eval_count"),
        }, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
