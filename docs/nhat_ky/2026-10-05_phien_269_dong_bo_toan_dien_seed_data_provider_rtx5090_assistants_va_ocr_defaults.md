# NHẬT KÝ PHIÊN LÀM VIỆC SỐ #269
**Ngày**: 2026-10-05  
**Tiêu đề**: Đồng Bộ Toàn Diện Dữ Liệu Seed CSDL PostgreSQL: Provider RTX 5090, Trợ Lý Soạn Thảo / Khảo Thí & Chuỗi OCR Combo Defaults  
**Kỹ sư phụ trách**: Senior Full-Stack Architect & Enterprise AI Systems Specialist  
**Mục tiêu**: Kiểm tra và trực tiếp commit dữ liệu cấu hình vào CSDL PostgreSQL (`model_provider_configs`, `assistants`, `system_model_defaults`), bảo đảm toàn bộ hạ tầng On-Premise GPU RTX 5090 (Tailscale MagicDNS) và mô hình `qwen3-vl:8b`, `deepseek-r1:32b` được kích hoạt 100% trong runtime.

---

### 1. Hiện Trạng & Vấn Đề Kỹ Thuật
1. **Trạng thái trước phiên**:
   - Các định nghĩa cấu hình đã được thêm vào hằng số code (`STANDARD_QNU_PROVIDERS`, `STANDARD_ASSISTANTS`, `DEFAULT_QNU_OCR_COMBO_CHAIN`).
   - Tuy nhiên, trong CSDL PostgreSQL thực tế, bảng `assistants` đã có sẵn các bản ghi cũ (`regulations`, `library`, `drafting`, `question_bank`, `admissions`) với `primary_model=gpt-4o-mini` hoặc `None`.
   - Hàm `seed_standard_assistants` trước đó chỉ cập nhật lại `name` khi `code in existing_by_code`, bỏ qua `config` nên cấu hình `preferred_provider_id="prov_rtx5090_ollama"` và `primary_model="deepseek-r1:32b"` chưa được áp vào DB.
   - Bảng `system_model_defaults` trong DB vẫn đang lưu giữ chuỗi `ocr_combo_chain` cũ (Priority 1 là Gemini Flash).

---

### 2. Các Thay Đổi & Giải Pháp Kỹ Thuật

#### 2.1. Nâng cấp Trình Seed Trợ Lý (`backend/app/modules/assistants/seeder.py`)
- Cập nhật logic nhánh `if code in existing_by_code:` để tự động cập nhật:
  - `existing_record.config = item["config"]` (chứa `primary_model`, `fallback_model`, `preferred_provider_id`).
  - `existing_record.description = str(item["description"])`.
  - `existing_record.system_prompt = str(item["system_prompt"])`.
- Giúp dữ liệu cấu hình chuẩn của hệ thống luôn đồng bộ ngay cả khi bản ghi đã tồn tại trong DB.

#### 2.2. Viết & Thực Thi Script Kích Hoạt Seed (`backend/scripts/inspect_and_sync_db.py`)
- Khởi tạo kết nối phiên `AsyncSessionFactory` và thực hiện 3 bước:
  1. `provider_service.seed_default_providers(db, overwrite=True)`: Commit nhà cung cấp `prov_rtx5090_ollama` (URL Tailscale MagicDNS `http://tormemrtxproto.tail0924dd.ts.net:11434`, 8 models hỗ trợ).
  2. `model_catalog_service.update_system_model_defaults(...)`: Đẩy `qwen3-vl:8b` trên `prov_rtx5090_ollama` lên vị trí Ưu tiên 1 trong `ocr_combo_chain`.
  3. `seed_standard_assistants(db)`: Cập nhật policy 2 trợ lý chuyên sâu (`drafting`, `question_bank`) sử dụng `deepseek-r1:32b` và `prov_rtx5090_ollama`.

---

### 3. Kết Quả Xác Nhận Trong CSDL PostgreSQL

```text
=== VERIFYING AFTER SYNC ===
[OK] prov_rtx5090_ollama found in DB! Name: QNU AI Server (RTX 5090 - Ollama), URL: http://tormemrtxproto.tail0924dd.ts.net:11434, Model: deepseek-r1:32b
     Models: ['deepseek-r1:32b', 'qwen3:8b', 'deepseek-r1:70b', 'qwen3-vl:32b', 'qwen3-vl:8b', 'qwen3-embedding:4b-q8_0', 'qwen3-embedding:8b', 'bge-m3:latest']
[OK] Assistant question_bank: primary_model=deepseek-r1:32b, provider=prov_rtx5090_ollama
[OK] Assistant drafting: primary_model=deepseek-r1:32b, provider=prov_rtx5090_ollama
[OK] System Defaults OCR Chain:
  * P1: prov_rtx5090_ollama - qwen3-vl:8b (active=True)
  * P2: prov_gemini - gemini-3.1-flash-lite (active=True)
  * P3: prov_mistral - mistral-ocr-latest (active=True)
  * P4: prov_openai - gpt-4o-mini (active=True)
```

---

### 4. Kiểm Thử Hệ Thống (Verification)
- **Database Query**: 100% bản ghi được ghi nhận chính xác trong PostgreSQL.
- **Frontend Fast-Path Verification**: `npm run build` hoàn thành trong 10.26s, 0 lỗi TypeScript, 0 lỗi cú pháp Vite.

---

### 5. Bài Học Kinh Nghiệm & Khuyến Nghị Tiếp Theo
- Khi viết các hàm Seeder khởi tạo hệ thống, cần luôn hỗ trợ chế độ đồng bộ cập nhật (`upsert`/`sync config`) thay vì chỉ kiểm tra `if exists: skip` để tránh tình trạng code đã đổi nhưng CSDL vẫn giữ cấu hình cũ.
- Chuỗi OCR Combo On-Premise hiện tại đã sẵn sàng phục vụ toàn bộ các luồng bóc tách văn bản scan của Trường ĐH Quy Nhơn mà không tốn chi phí API token đám mây.
