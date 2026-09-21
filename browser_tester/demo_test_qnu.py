"""Demo test script for browser-use on QNU AI Platform.

Chạy thử nghiệm tự động hóa trình duyệt với Gemini 2.5 Flash.
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Tự động nạp API key từ .env trong thư mục browser_tester
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from browser_use.agent.service import Agent
from browser_use.browser.profile import BrowserProfile
from browser_use.llm.models import ChatGoogle


async def run_qnu_test():
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("LỖI: Chưa cấu hình GEMINI_API_KEY trong file .env!")
        return

    print("=== Khởi tạo Trình duyệt & AI Tester ===")
    
    # 1. Cấu hình mô hình Vision AI
    llm = ChatGoogle(
        model="gemini-2.5-flash",
        api_key=gemini_key,
    )

    # 2. Cấu hình trình duyệt (headless=False để hiển thị cửa sổ Chromium trực quan)
    browser_profile = BrowserProfile(
        headless=False,
        disable_security=True,
    )

    # 3. Kịch bản kiểm thử bằng ngôn ngữ tự nhiên
    task_prompt = """
    1. Truy cập vào trang web: https://qnu.edu.vn
    2. Quan sát trang chủ, tìm mục hoặc liên kết liên quan đến 'Tuyển sinh'
    3. Click vào mục 'Tuyển sinh' hoặc liên kết thông tin tuyển sinh
    4. Đọc tiêu đề trang vừa vào và tóm tắt ngắn gọn 2 thông tin nổi bật trên màn hình.
    """

    print(f"Mệnh lệnh giao cho AI:\n{task_prompt}\n")
    print("Đang mở trình duyệt và thực thi tác vụ...")

    agent = Agent(
        task=task_prompt,
        llm=llm,
        browser_profile=browser_profile,
    )

    # 4. Thực thi và in kết quả
    history = await agent.run()
    
    print("\n=== KẾT QUẢ KIỂM THỬ HOÀN THÀNH ===")
    print(history.final_result())


if __name__ == "__main__":
    asyncio.run(run_qnu_test())
