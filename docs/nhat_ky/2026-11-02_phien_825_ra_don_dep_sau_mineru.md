# Phiên825 — Rà dọn dẹp sau chuyển MinerU

User xác nhận đã gỡ Nemotron trên server, hỏi nên dọn gì. Áp dụng clean-code/ModelOps skills, chỉ audit, chưa disable/xóa/restart/push hoặc inference.

DB chính đọc transaction READ ONLY xác minh OCR hệ thống và3workspace đã cấu hình dùng MinerU active; Nemotron vẫn active trong catalog. Lượt823 thật dùng MinerU task32trang; chất lượng824 chỉ mẫu. Profile E2E qnu-server vẫn OCR Nemotron/input4096/prompt hash; runner truyền profile này cho provider-setup. Ưu tiên đồng bộ runner/profile rồi disable model Nemotron cũ, không đụng QNUchat/embed/rerank và lịch sử.

Inventory cache trực tiếp đo khoảng37,30MiB (không gồm mọi pycache sâu), distFE4,03+8,67MiB. Không xóa cache khi còn dev dùng. Quét toàntmp quá rộng đã ngắt; không báo dung lượng toàntmp. Tmp120thư mục gồm Git worktree detached release-v1.0.3 và E2E93faa11f0caf còn5container Up, nên không xóa cảtmp/prunevolume. Giữ nguồn/rawZIP/canonical/review/report/hash và DB/index, node_modules/.venv; chưa audit đủ để xóa backend/frontend cũ hoặc adapter Nemotron.

Artifact cục bộ: `tmp/cleanup825/recommendations.md`, `inventory.json`, `db-readonly.json` chỉ metadata an toàn. Kiểm thực: Git status/worktree list, rg targeted, Docker ps, đọc config/registry/execution, SQLreadonly và inventoryPython exit0. Không test app vì không đổi hành vi. Task này chỉ bổ sung report/memory, giữ mọi thay đổi trước.

Bước tiếp theo được đề xuất, chưa thực hiện: sửa E2E MinerU contract/hướng dẫn; disable model cũ qua ModelOps; chốt diff; sau đó dọn cache/sandbox đã xác minh không dùng, giữ báo cáo và OCR. Dẫn xuất app chỉ dọn qua preview/action storage-cleanups.
