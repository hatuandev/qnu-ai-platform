# NHẬT KÝ LÀM VIỆC — PHIÊN #131
# Ngày: 2026-09-19 | Triển Khai Giai Đoạn C: Mã Hóa Provider Secrets & Migration Dữ Liệu Cũ

## 1. Mục Tiêu Phiên Làm Việc
Triển khai **Giai đoạn C: Mã hóa Provider Secrets và chuyển đổi dữ liệu cũ** theo hướng dẫn tại [08_huong_dan_cai_thien_code_tang_diem_danh_gia.md](../ke_hoach/08_huong_dan_cai_thien_code_tang_diem_danh_gia.md):
- Loại bỏ hoàn toàn rủi ro lưu trữ API Key ở dạng Plaintext trong CSDL PostgreSQL.
- Xây dựng công cụ migration secrets chuyên biệt hỗ trợ 3 chế độ: `--dry-run`, `--apply`, `--verify`.
- Hỗ trợ cơ chế Key Rotation an toàn khi thay đổi `PROVIDER_ENCRYPTION_KEY`.
- Tích hợp vào CLI quản trị hệ thống `python -m app.cli secrets`.
- Bổ sung unit test suite chuyên biệt và kiểm thử toàn diện trên CSDL live thật.

---

## 2. Các Thay Đổi Kỹ Thuật (Key Changes)

### 2.1. Nâng Cấp Crypto & Key Rotation ([`backend/app/core/crypto.py`](../../backend/app/core/crypto.py) & [`backend/app/core/config.py`](../../backend/app/core/config.py))
- **Key Rotation Fallback**: Thêm `OLD_PROVIDER_ENCRYPTION_KEYS` vào cấu hình. Khi `decrypt_secret()` gặp token không giải mã được bằng key hiện tại, tự động thử lần lượt các key cũ trong danh sách rotation.
- **Hàm `reencrypt_secret()`**: Giải mã token (bằng active key hoặc older key) và mã hóa lại bằng active key mới nhất, hỗ trợ chu kỳ xoay vòng khóa không gây downtime.
- **Hàm `_derive_fernet()`**: Tạo Fernet key 32-byte an toàn từ chuỗi secret bất kỳ qua SHA-256.

### 2.2. Xây Dựng Công Cụ Migration Secrets ([`backend/scripts/migrate_provider_secrets.py`](../../backend/scripts/migrate_provider_secrets.py))
Script hỗ trợ 3 chế độ độc lập:
1. `--dry-run`: Quét toàn bộ bảng `model_provider_configs`, phân loại `encrypted`, `plaintext`, `empty`, `corrupted` cho cả Primary API Key và các keys trong `extra_config["api_keys"]`. In báo cáo bảng mà KHÔNG sửa đổi CSDL.
2. `--apply`: Mở database transaction, mã hóa toàn bộ các key plaintext thành token `enc:v1:...`, cập nhật masked value, re-encrypt các key cũ và commit. Tuyệt đối không log secret thô ra console.
3. `--verify`: Kiểm định 100% bản ghi: xác nhận zero plaintext còn sót lại và tất cả các ciphertext đều giải mã thành công trong runtime. Trả về exit code 0 nếu pass, 1 nếu vi phạm.

### 2.3. Tích Hợp CLI Quản Trị ([`backend/app/cli.py`](../../backend/app/cli.py))
Bổ sung nhóm lệnh `secrets`:
```bash
# Kiểm tra trạng thái mã hóa (read-only audit)
uv run python -m app.cli secrets check

# Chạy migration mã hóa
uv run python -m app.cli secrets migrate --apply

# Kiểm định an toàn 100%
uv run python -m app.cli secrets migrate --verify
```

### 2.4. Bổ Sung Unit Test Suite Chuyên Biệt ([`backend/tests/test_migrate_secrets.py`](../../backend/tests/test_migrate_secrets.py))
Xây dựng 6 test cases mới:
- `test_crypto_key_rotation`: Kiểm tra giải mã token của key cũ và re-encrypt sang key mới.
- `test_inspect_secrets_classification`: Phân loại chính xác encrypted, plaintext, empty.
- `test_migrate_apply_encrypts_and_commits`: Xác nhận apply mã hóa cả primary lẫn pool keys và commit transaction.
- `test_migrate_verify_passes_when_all_encrypted`: Verify pass khi 100% encrypted.
- `test_migrate_verify_fails_when_plaintext_found`: Verify fail (exit code 1) khi có plaintext.
- `test_migrate_dry_run_executes`: Chạy dry-run không lỗi.

---

## 3. Kết Quả Kiểm Thử & Thực Thi CSDL Live (Verification)

1. **CSDL Live Audit Ban Đầu (`--dry-run`)**:
   - Phát hiện 4 Primary API Keys plaintext (`prov_mistral`, `prov_cloudflare`, `prov_openai`, `prov_gemini`).
   - Phát hiện 5 Key Pool Keys plaintext.
   - Tổng cộng 9 keys nhạy cảm cần mã hóa.
2. **CSDL Live Apply (`--apply`)**:
   - Mã hóa thành công 100% cho 5 providers trong database transaction.
   - Kết quả sau apply: 4 primary encrypted, 5 pool encrypted, **0 plaintext**.
3. **CSDL Live Verify (`--verify`)**:
   - `VERIFICATION PASSED: 100% of provider secrets are encrypted.`
   - `Zero plaintext secrets found. All ciphertexts decrypt successfully.`
4. **Backend Test Suite**:
   - `uv run ruff check .` -> All checks passed! (0 lỗi)
   - `uv run --extra dev pytest -v` -> **263/263 passed (100%), 0 warnings (50.00s)**
5. **Zero Mojibake**:
   - 337/337 tệp sạch UTF-8.
