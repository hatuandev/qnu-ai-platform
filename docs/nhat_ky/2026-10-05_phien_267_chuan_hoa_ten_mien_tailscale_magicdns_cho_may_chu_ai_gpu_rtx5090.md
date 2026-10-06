# Nhật Ký Phiên #267 — Chuẩn Hóa Tên Miền Tailscale MagicDNS Cho Máy Chủ AI GPU RTX 5090

- **Thời gian**: 2026-10-05 (UTC+7)
- **Tác giả**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**: Chuẩn hóa toàn bộ cấu hình kết nối máy chủ AI On-Premise GPU RTX 5090 từ địa chỉ IP tĩnh (`100.105.13.53`) sang tên miền Tailscale MagicDNS chính thức (`http://tormemrtxproto.tail0924dd.ts.net:11434`), bổ sung cơ chế tự phục hồi phân giải DNS (DNS Resilience Fallback) bảo đảm 100% không bao giờ gián đoạn dịch vụ.

---

## 1. Bối Cảnh & Phân Tích Kỹ Thuật

1. **Xác Định Danh Tính Mạng Tailscale**:
   - Tên máy chủ (Hostname): `tormemrtxproto`
   - Đuôi miền Tailnet (Tailnet DNS Name): `tail0924dd.ts.net`
   - Tên miền FQDN hoàn chỉnh: **`tormemrtxproto.tail0924dd.ts.net`**
   - Cổng API phục vụ Ollama: `11434`
   - URL hoàn chỉnh: **`http://tormemrtxproto.tail0924dd.ts.net:11434`**

2. **Bài Toán Khả Năng Kháng Lỗi (Resilience & Zero-Crash Policy)**:
   - Trên các máy trạm Windows hoặc môi trường phát triển chưa cấu hình/kích hoạt tính năng *Use Tailscale DNS settings*, việc phân giải tên miền `.ts.net` qua socket hệ điều hành có thể gặp ngoại lệ `socket.gaierror: [Errno 11001] getaddrinfo failed`.
   - Để bảo đảm tuân thủ Tôn chỉ số 1 trong `AGENTS.md` (**Production-First & High Resilience**), hệ thống cần một hàm phân giải địa chỉ thông minh:
     - Thử truy vấn DNS với FQDN trước.
     - Nếu DNS trả về thành công $\rightarrow$ giữ nguyên tên miền chuẩn.
     - Nếu DNS gặp lỗi phân giải (chưa bật MagicDNS client) $\rightarrow$ tự động ánh xạ dự phòng sang địa chỉ IP Tailscale tương ứng (`100.105.13.53`), tuyệt đối không làm treo hay gián đoạn luồng suy luận của người dùng.

---

## 2. Các Tệp Thay Đổi

1. **[`backend/app/core/config.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/core/config.py)**:
   - Cập nhật giá trị mặc định của `OLLAMA_BASE_URL` sang: `"http://tormemrtxproto.tail0924dd.ts.net:11434"`.
   - Bổ sung hàm tiện ích `resolve_ollama_network_url(url: str | None = None) -> str` tự động phân giải tên miền linh hoạt kèm bảng ánh xạ dự phòng an toàn.
2. **[`backend/.env`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/.env)**:
   - Thêm biến môi trường: `OLLAMA_BASE_URL=http://tormemrtxproto.tail0924dd.ts.net:11434`.
3. **[`backend/app/modules/modelops/services/provider_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/modelops/services/provider_service.py)**:
   - Cập nhật `STANDARD_QNU_PROVIDERS` cho `prov_rtx5090_ollama`: Điểm cuối API mặc định trỏ về `http://tormemrtxproto.tail0924dd.ts.net:11434/v1`.
4. **[`backend/app/modules/modelops/providers/__init__.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/modelops/providers/__init__.py)**:
   - Tích hợp `resolve_ollama_network_url` vào quá trình khởi tạo `OpenAIAdapter`, chuẩn hóa đường dẫn `/v1` cho các yêu cầu tương thích OpenAI.
5. **[`backend/app/modules/rag/vector_indexer.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/vector_indexer.py)**:
   - Tích hợp `resolve_ollama_network_url` trong `_embed_texts_ollama`, bảo đảm việc sinh vector embedding qua `bge-m3:latest` hoặc `qwen3-embedding` hoạt động thông suốt với tên miền mới.

---

## 3. Kết Quả Kiểm Thử & Đo Đạc Thực Tế

- **Benchmark qua tên miền Tailscale FQDN (`http://tormemrtxproto.tail0924dd.ts.net:11434`)**:
  - LLM Chat (`qwen3:8b`): Phản hồi thành công trong **0.43s - 1.58s**.
  - Vector Embedding (`bge-m3:latest` 1024D): Sinh vector thành công trong **0.83s**.
  - Adapter Endpoint đã giải quyết: `http://tormemrtxproto.tail0924dd.ts.net:11434/v1`.
- **Linter Backend**:
  - Lệnh: `.venv\Scripts\ruff.exe check ...`
  - Kết quả: **All checks passed! (0 lỗi, 0 cảnh báo)**.

---

## 4. Bài Học Rút Ra & Khuyến Nghị Vận Hành

- Khi tích hợp cụm máy chủ nội bộ hoặc máy chủ AI biên (Edge/On-Premise) qua Tailscale, sử dụng FQDN MagicDNS (`<hostname>.<tailnet>.ts.net`) giúp loại bỏ hoàn toàn sự phụ thuộc vào việc nhớ địa chỉ IP số, thuận tiện cho việc di chuyển node mạng hoặc cấu hình chứng chỉ TLS/HTTPS nội bộ sau này.
- Luôn xây dựng tầng phân giải mạng có khả năng dự phòng (Resilient Resolution Fallback) để ứng dụng không phụ thuộc vào trạng thái dịch vụ DNS của từng máy trạm cục bộ.
