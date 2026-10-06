# Architecture

## Core stack
- React 19 + TypeScript + Vite
- Tailwind CSS 4
- shadcn-style source components + Radix
- TanStack Router (file-based routing)
- TanStack Query
- TanStack Table
- TanStack Form + Zod
- cmdk command menu
- Sonner notifications
- Biome

## Routing
The TanStack Router Vite plugin scans `src/routes` and generates `src/routeTree.gen.ts`. The plugin must be listed before the React plugin in `vite.config.ts`.

## M1 runtime and transport foundation

- `src/app/config/runtime.ts` resolves non-secret runtime values from optional `window.__QNU_KTX_CONFIG__` first, then Vite env values, then same-origin defaults.
- `VITE_API_BASE_URL` defaults to `/api` and `VITE_BFF_BASE_URL` defaults to `/bff`.
- `src/app/api/client.ts` is the single fetch-based transport foundation. It sends `credentials: "include"`, serializes JSON bodies, supports `FormData`, and normalizes `ProblemDetails` into `ApiError`.
- `apiClient` and `bffClient` share the same implementation; feature code should not add another HTTP wrapper.
- `src/app/auth` owns the `/bff/user` current-user query and exposes BFF login/logout navigation. It does not store access tokens or implement OIDC in the browser.
- `/signin-oidc` and `/signout-callback-oidc` remain backend-owned callback paths and are not client-side routes.

Runtime injection can be provided by the hosting document before the application module loads:

```html
<script>
  window.__QNU_KTX_CONFIG__ = {
    apiBaseUrl: "/api",
    bffBaseUrl: "/bff"
  };
</script>
```

`VITE_AUTH_MODE=demo` is an explicit local-only mode for the design-system/demo experience. The default is `bff`, which checks the existing cookie session through `/bff/user`.

## M2 session and authorization bridge

- `src/app/auth/auth-gate.tsx` protects every route in the admin shell except `/sign-in` and `/access-denied`.
- `AuthGate` starts the backend-owned BFF login flow directly after an unauthenticated `/bff/user` response. `/sign-in` remains available as an explicit fallback page and preserves a safe local `redirect` search value. OIDC callback paths remain backend-owned.
- `/access-denied` is a public presentation route for authorization failures.
- `src/rbac/backend-role-map.ts` maps the backend `Administrator` role to every key in the existing `src/rbac/catalog.ts`. Unknown backend roles receive no permissions. This is a bridge to the existing catalog, not a second role catalog.
- The demo role switcher and demo role mutations are available only when `VITE_AUTH_MODE=demo`. In BFF mode the account menu uses the current user and invokes the real BFF logout path.

M2 does not migrate feature data to the API. Feature-level API hooks and permission-aware navigation remain later migration work.

## M3 shell and real navigation

- `RbacProvider` exposes `isAccessVerified` and `accessSource` so shell consumers can distinguish backend-derived access from the explicit demo mode.
- In BFF mode, permissioned navigation is rendered only after the authenticated current user and backend-role bridge are available. Unknown backend roles produce no permissioned navigation.
- `AppSidebar` and `CommandMenu` both derive their permissioned entries from `navigation/config.ts` and the same RBAC `can` function. No second navigation list or UI-only access rule is introduced.
- Direct URLs remain protected by route-level permission checks and render `AccessDenied` when a user reaches a route that is not present in the filtered navigation.
- The topbar/sidebar account surfaces use BFF identity and the account menu invokes backend logout outside demo mode. Mobile drawer behavior, theme switching and callback paths remain owned by the existing shell/backend contracts.

## Folders
- `app`: providers and app-wide infrastructure.
- `components/ui`: low-level UI primitives.
- `components/admin`: reusable admin compositions.
- `layouts`: admin shell/sidebar/topbar/command composition.
- `navigation`: the only navigation source.
- `rbac`: permission catalog and demo permission context.
- `features`: feature-level components and models.
- `routes`: route orchestration.
- `styles`: tokens and global design contract.

## Reference feature
`/users` intentionally exercises Input, Select, Button, Checkbox, DropdownMenu, Table, Badge, pagination, sorting, URL search state and RBAC.

## RBAC management
- `src/rbac/catalog.ts` is the only permission catalog. Permission keys, labels, resources and descriptions are defined there and inferred into `PermissionKey`.
- `src/rbac/demo.ts` contains the initial runtime role records. `RbacProvider` owns the demo role state, including custom roles, assignments and the current demo role.
- `src/rbac/policy.ts` centralizes system-role restrictions: system roles cannot be deleted or renamed, and custom roles with assigned users cannot be deleted.
- `/roles` is the role management reference: URL-filtered table, create/edit/duplicate/detail flows, role-level permissions and guarded actions.
- `/permissions` is the catalog view plus a role-centric permission editor with search, resource select-all, dirty state and save/cancel.
- Direct route guards use `roles.read` and `permissions.read`; action visibility uses the matching create/update/delete permissions.
- Users, invitations and the demo-role switcher read `roles` from `RbacProvider`, so newly created custom roles are available without a second role catalog.

## Application patterns
- `src/components/admin/settings-section.tsx`, `settings-row.tsx` and `settings-save-bar.tsx` provide the shared settings hierarchy, preference row and dirty/save footer patterns.
- Settings routes share `SettingsLayout` with desktop side navigation and a compact mobile selector. General settings use TanStack Form + Zod; notification and security preferences use controlled local demo state.
- Profile uses its own `profile.read`/`profile.update` permissions and reuses the settings save pattern. Theme selection is connected to the existing global `ThemeProvider`.
- Activity events live in `features/activity` as a generic event model and feed pattern with URL search/type/actor filters, grouping, loading/empty/error states and a detail Sheet.
- Password, sessions, two-factor and avatar interactions are representative UI-only flows. They do not persist secrets, upload files or implement authentication infrastructure.

## Data visualization
- Recharts is the single chart foundation for `/dashboard`, `/analytics` and the `/design-system` gallery. Feature-level chart components own the meaning of each visualization; there is no universal chart abstraction.
- `components/admin/chart-card.tsx`, `kpi-metric.tsx` and `time-range-select.tsx` provide the reusable admin patterns. `features/analytics` owns deterministic demo data, formatting and chart semantics.
- Dashboard and analytics keep the time range in TanStack Router search state (`7d`, `30d`, `90d`, `1y`) with Zod fallback to `30d`.
- Chart colors use the restrained semantic `--chart-1` through `--chart-4` tokens in `styles/tokens.css`; charts remain frontend/demo-only until a later data source is introduced.

## M4 Buildings feature

- `features/buildings/api.ts` is the first ClientApp domain API module. It calls `/api/DormitoryBuildings` through the shared `apiClient`, preserves backend PascalCase query names and uses the server pagination envelope.
- `/ktx/buildings` keeps search, status, page and page-size in TanStack Router search state validated by Zod. The detail route is `/ktx/buildings/$buildingId`.
- The table uses TanStack Table and shared DataTable pagination/view-options, with loading, API error, empty, filter-empty and permission-aware action states.
- Create/edit uses TanStack Form + Zod with the responsive Dialog/Sheet composition. Deactivation uses the backend transition endpoint and invalidates list/detail queries after success.
- Building permissions are added to the existing permission catalog as `buildings.read`, `buildings.create`, `buildings.update` and `buildings.deactivate`; no second RBAC catalog or CRUD framework is introduced.

## M5 Catalog and academic setup

- `features/floors` calls the nested `/api/DormitoryBuildings/{buildingId}/Floors` contract. The list keeps the selected building and local search/status filters in the URL, while detail routes preserve both building and floor identifiers.
- `features/room-types` calls `/api/RoomTypes` with backend-compatible `SearchCodeOrName`, `IsActive`, `PageIndex` and `PageSize` parameters. The list, detail, create/edit form and deactivate transition follow the M4 table and responsive form compositions.
- `features/academic-years` calls `/api/AcademicYears` and keeps current/archive filtering, pagination and detail navigation in search state. Date-only values are converted explicitly between `yyyy-MM-dd` storage semantics and the shared `dd/MM/yyyy` DatePicker display.
- `features/semesters` calls `/api/Semesters`, uses the academic-year filter as a dependent catalog selection, constrains DatePicker bounds to the selected academic year and preserves the backend DELETE soft-deactivate contract.
- M5 permissions are resource-specific (`floors.*`, `roomTypes.*`, `academicYears.*`, `semesters.*`) and are added to the existing catalog. Administrator receives the demo permissions; other demo roles continue to exercise access-denied behavior.
- No backend endpoint, DTO, legacy ClientApp code or universal CRUD framework was introduced. API response adapters reject malformed SPA-fallback responses so unavailable backend data is shown as an error rather than a false empty state.

## M6 Student operations and service workflows

- `features/students` calls `/api/Students` with server-side search, faculty/status filters and pagination. Student identity is synchronized automatically from UIS after SSO sign-in; there is no manual link/unlink workflow.
- `features/applications` calls `/api/DormitoryApplications` and `/api/ApplicationReviews`. Application detail renders backend status history and review transitions without simulating approval state in the browser.
- `features/notifications` calls `/api/Notifications` for administrator list/detail/create flows. Recipient selection uses the existing Students API and sends the backend's `StudentRecipientIds` contract.
- `features/support` calls `/api/SupportRequests` for list/detail/create/process/comments/history. Server-side student scoping remains authoritative; ClientApp does not duplicate that policy.
- M6 list state is URL-backed through TanStack Router + Zod, data is server state through TanStack Query, tables use TanStack Table and mutations invalidate affected queries.
- M6 permissions (`students.*`, `applications.*`, `notifications.*`, `support.*`) extend the single RBAC catalog. No second role catalog, universal CRUD framework or backend/auth implementation was added.

## M7 Operations workflows

- `features/assignments` models the approved-application → room-capacity sequence and uses `/api/RoomAssignments` for eligibility, available-place checks, assignment and cancellation. The UI does not duplicate capacity or student uniqueness rules.
- `features/residences` models check-out, transfer and extension as explicit actions over `/api/Residences`, with detail/history queries and shared DatePicker surfaces for date-bearing commands.
- `/ktx/assignments` and `/ktx/residences` keep filters and pagination in TanStack Router search state. Tables remain TanStack Table instances, and mutations invalidate list/detail/history queries through TanStack Query.
- M7 permissions (`assignments.*`, `residences.*`) extend the one RBAC catalog. Navigation and direct route guards use the same permission context.

## Application chrome polish
- `components/admin/account-menu.tsx` is the shared account-menu content used by both the topbar avatar and the sidebar footer. Demo role switching is kept in a submenu, and sign-out is explicitly informational until authentication exists.
- `components/admin/notifications-popover.tsx` reuses Stage 5 activity events for a lightweight notification preview. `quick-create-menu.tsx` routes into the existing Users/Roles create flows through URL state.
- Search uses the existing `Ctrl/Meta + K` handler and displays a platform-aware shortcut. The command palette preserves navigation hierarchy through grouped sections and searchable parent labels.
- `components/ui/textarea.tsx` is the canonical shadcn-style textarea source component used by profile, role forms and the design-system gallery. Form/detail sheets use near-full mobile width while the sidebar drawer keeps its own width override.
- Radius and elevation are semantic: controls use 6px, normal surfaces and overlays use 8px, controls have no decorative shadow, floating overlays use `shadow-sm` and modal surfaces use `shadow-md`.
- `components/ui/tabs.tsx`, `radio-group.tsx`, `alert.tsx` and `progress.tsx` are Radix-backed or token-backed primitives. `components/admin/empty-state.tsx` and `field.tsx` provide reusable non-table empty and form-message compositions.
