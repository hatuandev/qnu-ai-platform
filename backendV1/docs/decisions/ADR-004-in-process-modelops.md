# ADR-004 — ModelOps trong cùng process

**Quyết định:** modelops là domain nội bộ (provider/key/catalog/inference/usage),
không tách microservice ở MVP. Domain khác chỉ gọi qua `modelops/public_api.py`.

**Hệ quả:** đơn giản triển khai; có thể tách sau nếu cần scale riêng.
