"""Kiểm thử tự động giao diện Web QNU AI Platform bằng browser-use.

Yêu cầu: Frontend đang chạy tại http://localhost:5173
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


async def run_local_app_test():
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("LỖI: Chưa cấu hình GEMINI_API_KEY trong file .env!")
        return

    print("=== Khởi tạo AI QA Tester cho QNU AI Platform ===")
    
    llm = ChatGoogle(
        model="gemini-2.5-flash",
        api_key=gemini_key,
    )

    browser_profile = BrowserProfile(
        headless=False,
        disable_security=True,
    )

    task_prompt = """
    1. Truy cập vào trang web ứng dụng nội bộ: http://localhost:5173/assistants
    2. Kiểm tra xem màn hình danh sách Trợ lý AI có tải thành công hay không.
    3. Tìm và xác nhận có thấy thẻ 'Trợ lý Tuyển sinh' (Admissions Assistant) không.
    4. Click vào Trợ lý Tuyển sinh để vào trang chi tiết.
    5. Kiểm tra xem có xuất hiện lỗi đỏ hoặc thông báo lỗi nào trên màn hình không.
    6. Báo cáo kết quả kiểm thử: TRẠNG THÁI GIAO DIỆN (ĐẠT / KHÔNG ĐẠT) và các thành phần đã kiểm tra.
    """

    print(f"Kịch bản kiểm thử:\n{task_prompt}\n")
    print("Đang chạy kiểm thử tự động...")

    agent = Agent(
        task=task_prompt,
        llm=llm,
        browser_profile=browser_profile,
    )

    history = await agent.run()
    
    print("\n=== BÁO CÁO KIỂM THỬ (QA REPORT) ===")
    print(history.final_result())


if __name__ == "__main__":
    asyncio.run(run_local_app_test())
