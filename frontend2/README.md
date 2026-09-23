# Admin Starter Core

A design-system-first admin foundation for React + Vite. It is intentionally small enough to understand but complete enough to continue with coding agents without re-deciding the UI architecture.

## What is included
- File-based TanStack Router setup.
- Tailwind CSS 4 semantic design tokens.
- Radix-backed shadcn-style primitives.
- Responsive Admin Shell with nested sidebar navigation.
- Command menu (`Ctrl/Cmd + K`).
- Light/dark theme.
- Demo RBAC with role switching.
- `/design-system` visual regression page.
- `/users` reference table with search/filter/sort/pagination/selection.
- Settings and placeholder routes for the next stages.
- Agent/design-system documentation.

## Install

```bash
npm install
npm run dev
```

To run the Web API, database and ClientApp through .NET Aspire from the
repository root:

```powershell
dotnet run --project .\src\AppHost\AppHost.csproj
```

AppHost starts this app as the `webfrontend` JavaScript resource and injects
the Web API endpoint used by the Vite proxy. Docker Desktop must be running
for the PostgreSQL container. Use `BYPASS_SSO=true` only for an explicitly
local backend test; otherwise the normal BFF/SSO flow remains authoritative.

The first Vite run generates `src/routeTree.gen.ts` through the TanStack Router Vite plugin. If your editor reports that file as missing before first run, start the dev server once.

Then validate:

```bash
npm run typecheck
npm run lint
npm run build
```

## Design-system rule
Do not mix UI foundations. This starter is Tailwind + shadcn/Radix only. Global CSS must not reset interactive HTML elements; shared primitives own their appearance.

## Continue development
Use `docs/NEXT_STAGE_PROMPT.md` as the next coding-agent prompt.

## References
The architecture follows current official shadcn/TanStack patterns. Shadcn Admin and TryCompAI CRM are design references only; this starter is not a clone of either product.
