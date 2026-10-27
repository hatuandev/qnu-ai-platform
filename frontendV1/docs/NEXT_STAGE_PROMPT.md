# Next Stage Prompt — Users Reference Feature Completion

Work directly in this project. Do not change the UI foundation, router, design tokens or folder layering.

## Goal
Turn `/users` into the reference production-quality admin feature while preserving the design-system contract.

## Required work
- Add URL state for page, pageSize and sort using TanStack Router + Zod.
- Add create/edit/view user flows using shared Dialog/Sheet compositions.
- Use TanStack Form + Zod for the shared create/edit form.
- Add bulk actions and column visibility.
- Add loading, empty, filter-empty and error states.
- Add permission-aware actions for `users.create`, `users.update`, `users.delete`.
- Keep roles as runtime strings sourced from the RBAC demo role catalog; do not create a second role catalog.
- Keep TanStack Table as the table engine.
- Do not create a universal CRUD framework.

## Design rules
- Do not create new Button/Input/Select/Dialog primitives.
- Any missing shadcn primitive should be added through the shadcn CLI using the project configuration and then reviewed on `/design-system`.
- Keep page title at the documented scale.
- Keep table cells 13px and headers 12px.
- Avoid large rounded cards and unnecessary shadows.

## Validation
Run `npm run typecheck`, `npm run lint`, and `npm run build`, then test `/design-system`, `/users`, `/users/invitations`, dark/light, desktop/mobile and demo role switching.

Stop after the Users reference feature is complete. Do not start backend/API/auth.
