# Kiến trúc backendV1

## Tầng

| Tầng | Vai trò | Không được làm |
|---|---|---|
| `api/` | Lắp ráp, dependency, handler lỗi, health | Chứa SQL hay nghiệp vụ |
| `platform/` | Config, DB, cache, storage, crypto, log, metric | Import domain |
| `contracts/` | DTO dùng chung (problem, page, idempotency, SSE) | Logic nghiệp vụ |
| `ports/` | Protocol ra hệ ngoài | Import SDK cụ thể |
| `adapters/` | Cài đặt port bằng SDK | Được import bởi domain |
| `domains/` | Router mỏng + service + policy + models | Import `adapters` |
| `workers/` | ARQ, queue riêng của v1 | Nhặt job legacy |

## Luồng một request

`HTTP → middleware (correlation, CORS) → dependencies (actor, db) → router → service → port → adapter`

## Quy tắc phụ thuộc

`api → domains → ports/contracts → platform`; `adapters` chỉ được `api/wiring` khởi tạo.
`domain` không import `api`, không import `adapters`.
