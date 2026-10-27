# ADR-003 — Cô lập runtime

**Quyết định:** v1 chạy cổng 8002, queue `qnu:v1:jobs`, cache `qnu:v1:cache:`,
worker riêng. Không nhặt job legacy, không chạy cron legacy.

**Hệ quả:** có thể tắt v1 bất kỳ lúc nào mà không ảnh hưởng hệ đang phục vụ.
