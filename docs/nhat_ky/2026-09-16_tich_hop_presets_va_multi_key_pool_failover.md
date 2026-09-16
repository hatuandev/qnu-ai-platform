# Nhật Ký Công Việc — Tích Hợp Presets & Multi-Key Pool Failover Theo qnu-ai-core

- **Thời gian**: 2026-09-16 11:15 (UTC+7)
- **Tác giả**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**: Nghiên cứu kiến trúc quản lý Provider của `qnu-ai-core`, tích hợp cấu hình sẵn của các provider đặc thù (OpenAI, Gemini, Claude, DeepSeek, Groq, OpenRouter, Mistral, Cloudflare Workers AI, NVIDIA NIM, Ollama, Local vLLM, Custom), hỗ trợ tạo Custom Provider, và thiết lập hệ thống Nhóm Khóa API (Key Pool / Multi-Key) tự động xoay vòng dự phòng JIT Failover khi một key chạm Rate Limit 429 hoặc cạn Token Quota.

---

## 1. Nội Dung Kỹ Thuật Đã Triển Khai

### A. Backend (`backend/app/modules/modelops/`)
1. **`schemas.py`**:
   - Khai báo danh mục `PROVIDER_PRESETS` gồm 12 mẫu nhà cung cấp với cấu hình Base URL mặc định, icon, mô tả và hướng dẫn lấy API key.
   - Thêm các schema cho Key Pool: `ProviderKeyItem`, `ProviderKeyCreate`, `ProviderKeyUpdate`, `SimulateKeyRotationRequest`, `SimulateKeyRotationResponse`, `ProviderKeyTestResponse`.
   - Bổ sung `api_keys`, `keys_count`, `account_id` vào `ProviderConfigCreate` và `ProviderConfigResponse`.
2. **`service.py`**:
   - Lưu trữ danh sách `api_keys` vào cột `extra_config["api_keys"]` trong bảng `model_provider_configs`.
   - Triển khai các hàm nghiệp vụ Key Pool: `get_provider_keys`, `add_provider_key`, `update_provider_key`, `delete_provider_key`, `test_provider_key`.
   - Cơ chế tự phục hồi Cooldown: hàm `_auto_recover_cooldown` tự động chuyển trạng thái `rate_limited` về `active` sau khi hết thời hạn cooldown (60s).
   - Hàm `simulate_key_rotation`: Mô phỏng tiêu thụ token và cơ chế tự động chuyển sang khóa dự phòng kế tiếp khi gặp sự cố Rate Limit 429.
   - Hàm `generate()`: Khi thực thi, duyệt qua Key Pool của Provider theo thứ tự ưu tiên. Nếu một key gặp lỗi 429, hệ thống đưa key đó vào cooldown 60s và lập tức thử lại với key kế tiếp trong pool trước khi chuyển fallback provider.
3. **`router.py`**:
   - Bổ sung endpoint `GET /presets` lấy danh mục presets.
   - Bổ sung 6 endpoints quản lý Key Pool: danh sách keys, thêm key, cập nhật key, xóa key, test key, mô phỏng xoay key.
4. **`tests/test_modelops.py`**:
   - Thêm `test_api_get_provider_presets` và `test_api_key_pool_crud_and_rotation`.

### B. Frontend (`frontend/src/`)
1. **`services/api-client.ts`**:
   - Định nghĩa `ProviderApiKey`, `ProviderPreset` và mở rộng `ModelProvider`.
   - Bổ sung 7 API client methods tương ứng: `getProviderPresets`, `getProviderKeys`, `addProviderKey`, `updateProviderKey`, `deleteProviderKey`, `testProviderKey`, `simulateKeyRotation`.
2. **`pages/modelops-page.tsx`**:
   - Thêm thanh chọn Mẫu Cấu Hình Sẵn (Presets) trong Dialog tạo mới Provider. Bấm chọn sẽ tự động điền Base URL, tên hiển thị, và các trường chuyên biệt như `Account ID` (Cloudflare).
   - Thêm badge số lượng API Keys trên mỗi Provider Card kèm nút bấm **"Key Pool"**.
   - Hộp thoại quản lý **Nhóm Khóa API (Key Pool)**: Hiển thị các key xếp theo độ ưu tiên `#1`, `#2`, tiến độ quota, badge trạng thái (`Sẵn Sàng`, `Cooldown 429`, `Hết Quota`, `Đã Tắt`), các nút thao tác Test key, Tạm tắt, Xóa.
   - Nút **"⚡ Mô Phỏng Xoay Key (Test 429 Failover)"** cho phép người dùng kiểm thử trực quan cơ chế chuyển key tự động khi 429 xảy ra.
3. **`tests/e2e/04_modelops_key_pool.spec.ts`**:
   - Bổ sung 3 test Playwright E2E cho giao diện Quản Lý Provider, Presets selection, và Key Pool actions.

---

## 2. Kết Quả Kiểm Thử Toàn Diện

- **Backend Lint**: `uv run ruff check .` → **0 lỗi**
- **Backend Pytest**: `uv run --extra dev pytest` → **70/70 passed** (100%)
- **Frontend Lint**: `npm run lint` → **0 lỗi** (Biome check 58 files)
- **Frontend Typecheck**: `npm run typecheck` → **0 lỗi** (`tsc --noEmit`)
- **Frontend Vite Build**: `npm run build` → **Thành công** (1,040 kB)
- **Playwright E2E**: `npm run test:e2e` → **15/15 passed** (100%)
