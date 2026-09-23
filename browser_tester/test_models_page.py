"""Kiểm thử tự động giao diện Quản lý Mô hình (/models) bằng browser-use.

Target: Frontend2 đang chạy tại http://localhost:3000/models
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from browser_use.agent.service import Agent
from browser_use.browser.profile import BrowserProfile
from browser_use.llm.models import ChatGoogle


async def run_models_page_test():
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("LỖI: Chưa cấu hình GEMINI_API_KEY trong file .env!")
        return

    print("=== Khởi tạo AI QA Tester cho QNU AI Platform - Trang /models ===")

    llm = ChatGoogle(
        model="gemini-2.5-flash",
        api_key=gemini_key,
    )

    browser_profile = BrowserProfile(
        headless=False,
        disable_security=True,
    )

    task_prompt = """
    1. Truy cập vào trang web ứng dụng: http://localhost:3000/models
    2. Kiểm tra tab 'Định Tuyến & Mặc Định Hệ Thống' (Routing & Defaults):
       - Xác nhận hiển thị đủ 4 khối Pipeline: 1. Nhúng Vector (Embedding), 2. Tái Xếp Hạng (Reranker), 3. Bóc Tách & OCR Thị Giác (Vision OCR), 4. Hội Thoại & Lý Luận (LLM Chat).
       - Thử click chuyển chế độ giữa 'Mô Hình Đơn' và 'Chuỗi Dự Phòng' tại kênh OCR hoặc Reranker để xem chuyển trạng thái có mượt không.
    3. Chuyển sang tab 'Chuỗi Dự Phòng & Combos':
       - Kiểm tra các thanh lọc tác vụ (OCR, Nhúng Vector, Tái Xếp Hạng, LLM Chat).
       - Kiểm tra danh sách các Card Combo hiển thị đầy đủ thông tin pipeline và các tầng mô hình.
    4. Bấm nút '+ Tạo Combo Mới':
       - Xác nhận Modal mở lên bình thường.
       - Kiểm tra 4 nút chọn Task Type: Vision OCR, Embedding, Reranker, LLM Chat có hiển thị đẹp và đồng bộ không.
       - Bấm nút Hủy hoặc đóng Modal.
    5. Đánh giá tính thẩm mỹ màu sắc: Xác nhận toàn bộ giao diện có tông màu chủ đạo Teal trang nhã đồng nhất, không còn các mảng nút màu cam hay tím chói lóa.
    6. Báo cáo kết quả kiểm thử (QA REPORT): Tóm tắt từng bước và kết luận ĐẠT / KHÔNG ĐẠT.
    """

    print(f"Kịch bản kiểm thử:\n{task_prompt}\n")
    print("Đang bắt đầu chạy kịch bản kiểm thử với browser-use...")

    agent = Agent(
        task=task_prompt,
        llm=llm,
        browser_profile=browser_profile,
    )

    history = await agent.run()

    print("\n=== BÁO CÁO KIỂM THỬ TỰ ĐỘNG (QA REPORT) ===")
    print(history.final_result())


if __name__ == "__main__":
    asyncio.run(run_models_page_test())
