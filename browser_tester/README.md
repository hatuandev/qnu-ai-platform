# QNU Browser Tester (Dựa Trên `browser-use`)

Môi trường kiểm thử tự động hóa trình duyệt web bằng Trí tuệ Nhân tạo (AI QA Testing & Web Automation) cho **QNU AI Platform**.

---

## 1. Cấu Trúc Thư Mục

- `.venv/`: Môi trường ảo Python 3.12 độc lập, không ảnh hưởng đến `backend` chính.
- `.env`: Chứa khóa API của Google Gemini (`GEMINI_API_KEY`) hoặc OpenAI (`OPENAI_API_KEY`).
- `demo_test_qnu.py`: Kịch bản mẫu truy cập cổng thông tin Đại học Quy Nhơn (`https://qnu.edu.vn`) và tra cứu tuyển sinh.
- `test_qnu_local_app.py`: Kịch bản kiểm thử giao diện Frontend ứng dụng QNU AI Platform (`http://localhost:5173`).

---

## 2. Cách Chạy Kịch Bản Kiểm Thử

### Kịch bản 1: Kiểm thử web ngoài (Cổng thông tin ĐH Quy Nhơn)
Mở PowerShell tại thư mục này hoặc từ thư mục gốc dự án:

```powershell
cd d:\DuAnPhanMem\qnu-ai-platform\browser_tester
uv run python demo_test_qnu.py
```

### Kịch bản 2: Kiểm thử giao diện ứng dụng QNU AI Platform
*(Đảm bảo Frontend đang chạy tại cổng 5173: `cd ../frontend && npm run dev`)*

```powershell
cd d:\DuAnPhanMem\qnu-ai-platform\browser_tester
uv run python test_qnu_local_app.py
```

---

## 3. Tùy Biến Cấu Hình

### Bật / Tắt hiển thị trình duyệt:
Trong file script, tìm `BrowserProfile`:
- `headless=False`: Bật cửa sổ Chromium để người dùng quan sát AI tự click trực tiếp.
- `headless=True`: Chạy ngầm trong nền, không hiện cửa sổ (thích hợp cho CI/CD server).

### Đổi mô hình LLM:
Có thể sử dụng các mô hình Vision mạnh mẽ trong `browser_use.llm.models`:
- `ChatGoogle(model="gemini-2.5-flash")` (Mặc định - tốc độ cao, tiết kiệm chi phí).
- `ChatGoogle(model="gemini-2.5-pro")` (Suy luận chuyên sâu).
- `ChatOpenAI(model="gpt-4o")` (Cần thêm `OPENAI_API_KEY` trong file `.env`).
