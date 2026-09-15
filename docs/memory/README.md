# Memory — Hệ Thống Bộ Nhớ Ngữ Cảnh Dự Án (Context Snapshot System)

Thư mục này lưu trữ **bộ nhớ ngữ cảnh** (Context Memory) của dự án `qnu-ai-platform` để bảo đảm liên tục giữa các phiên làm việc của AI Agent. Mỗi khi bắt đầu một phiên mới, Agent phải đọc `PROJECT_CONTEXT.md` trước tiên; khi kết thúc, phải ghi lại snapshot ngữ cảnh cập nhật.

---

## Cấu Trúc Thư Mục

```
docs/memory/
├── README.md                    # Tài liệu này — hướng dẫn hệ thống
├── PROJECT_CONTEXT.md           # ★ Snapshot ngữ cảnh dự án hiện tại (LUÔN CẬP NHẬT)
└── snapshots/                   # Lưu trữ snapshot theo phiên (KHÔNG XÓA)
    ├── 2026-09-15_session_01.md
    ├── 2026-09-15_session_02.md
    └── ...
```

## Quy Tắc Vận Hành

| Thời Điểm | Hành Động Bắt Buộc |
| :--- | :--- |
| **Đầu phiên** | Đọc `PROJECT_CONTEXT.md` để nắm trạng thái hiện tại |
| **Cuối phiên** | Cập nhật `PROJECT_CONTEXT.md` + lưu snapshot vào `snapshots/` |
| **Sau sự cố** | Đọc snapshot gần nhất để phục hồi ngữ cảnh |
