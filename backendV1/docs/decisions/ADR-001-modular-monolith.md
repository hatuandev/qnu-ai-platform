# ADR-001 — Modular monolith FastAPI

**Trạng thái:** chấp thuận (Phase 0).

**Bối cảnh:** legacy là một package 95k dòng, biên giới mờ; Nexora (.NET) dùng CQRS/MediatR.

**Quyết định:** giữ FastAPI + SQLAlchemy async + ARQ; tổ chức theo domain, không CQRS,
không MediatR. Router mỏng, service rõ, policy thuần.

**Hệ quả:** ít ceremony hơn CQRS; cần kỷ luật import-linter để giữ biên giới.
