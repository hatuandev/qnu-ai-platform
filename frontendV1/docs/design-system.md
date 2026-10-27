# Design System Contract

## Goal
A restrained, neutral, enterprise admin language inspired by good patterns from Shadcn Admin and data-dense CRM products without copying business-specific UI.

## Layers
1. `styles/tokens.css` — semantic tokens.
2. `components/ui` — primitives.
3. `components/admin` — reusable admin patterns.
4. `features` — feature composition.
5. `routes` — orchestration.

Dependencies flow downward only.

## Typography
- Page title: 30px desktop / 26px mobile.
- Section title: 18px.
- Body: 14px.
- Card and dialog titles: 16px.
- Controls: 14px.
- Compact toolbar controls (search, filter selects, toolbar buttons): 12px.
- Navigation: 14px / semibold.
- Table cells: 14px desktop / 12px mobile.
- Table headers: 12px / semibold / muted-foreground.
- Secondary text: 13px.
- Caption/meta: 12px.
- Group headings and eyebrows: 11–12px / semibold.
- 10px is not a normal body/control/navigation/table size.

## Density
- Default controls: 36px.
- Small controls: 32px.
- Compact toolbar buttons: `size="sm"` with `text-xs` and `size-3.5` icons.
- Table rows: approximately 44–48px depending on content.
- Sidebar rows: 36px.
- Topbar: 56px.
- Popup menu items: 36–40px, 14px text, 16px icons, 8–10px icon gap.
- Standard dropdown width: 200–240px; workspace/account menus: 240–260px.
- Popup content padding: 6px with a restrained overlay shadow.

## Surfaces and elevation
Prefer borders, separators and spacing. Feature list/table cards and workflow summary panels use `rounded-xl` with `shadow-2xs` as the elevated surface style. Floating overlays use a restrained `shadow-sm`; dialogs and sheets use `shadow-md` because they sit above the page.

## Radius
Radius V3 is intentionally compact:

- Micro controls and menu details: 4px (`--radius-micro` / `rounded-sm`).
- Button, Input, Select and Textarea: 6px (`--radius-control` / `rounded-md`).
- Cards, dropdowns, popovers and dialogs: 8px (`--radius-surface` / `rounded-lg`).
- Feature list/table cards and workflow summary panels: 12px (`rounded-xl`) with `shadow-2xs`.
- Avatars, switches, progress tracks and semantic pill badges keep their full radius.
- Do not use `rounded-2xl` or larger for normal admin surfaces.

The compatibility `--radius` token is 6px. `--radius-micro`, `--radius-control`, `--radius-surface` and `--radius-overlay` are defined in `styles/tokens.css`.

## Compact toolbar pattern
List-page toolbars use a compact density contract:

- Search input: `text-xs`, icon prefix, `sm:max-w-xs`.
- Filter selects: `text-xs` with fixed widths (`sm:w-40`–`sm:w-60`).
- Action buttons: `size="sm"`, `text-xs`, `size-3.5` icons.
- Toolbar wraps to a full-width column on mobile (`flex-col w-full sm:flex-row sm:w-auto`).
- Keep the same contract across all list pages.

## Dialog pattern
Form/action dialogs use a structured layout:

- `ResponsiveDialogContent` with `p-0 gap-0`, max height `max-h-[min(820px,calc(100vh-2rem))]`.
- Bordered header: `border-b bg-muted/20`, icon tile (`size-8 rounded-lg bg-muted`) + title, `text-xs` description.
- Scrollable body: `min-h-0 flex-1 overflow-y-auto`.
- Bordered footer: `border-t bg-card`, 2-column grid on mobile, right-aligned row on desktop.

## Workflow summary pattern
Workflow/status summary panels:

- 2-panel grid (`lg:grid-cols-12`, left 7 / right 5) with `divide-x` on desktop.
- Capacity/progress bars are stacked segments using semantic tokens (`bg-success` finalized, `bg-info` pending).
- KPI mini-cards: 2x2 grid, `text-[11px]` labels, `text-xl` mono values, `text-[11px]` hints.
- Status dots inside badges use semantic tokens (`bg-success`, `bg-info`, `bg-warning`, `bg-muted-foreground/60`).

## Field pattern
Use `components/admin/field.tsx` for shared form rhythm:

1. `Field`
2. `FieldLabel`
3. shared control
4. `FieldDescription` when context is needed
5. `FieldError` with `aria-describedby` where practical

TanStack Form and Zod remain the form state and validation layers. The field components only standardize structure and typography.

## Feedback pattern
- Use `Alert` for persistent contextual information or warnings.
- Use Sonner toast for transient success/error/info feedback.
- Use `Progress` for horizontal completion or usage values from 0–100.
- Use `EmptyState` for non-table empty surfaces; keep `DataTableEmpty` for table-specific geometry.
- Use Skeleton for page/content loading and a small button spinner for short submit actions.

## Date conventions
Date controls use Vietnamese presentation defaults: `dd/MM/yyyy`, `dd/MM/yyyy HH:mm` and `MM/yyyy`. These formats are centralized in `src/lib/date-utils.ts`; never parse a display value with `new Date(string)`. Calendar dates remain local calendar semantics and must not be converted through UTC just to display them.

- `DateInput` supports direct keyboard entry and explicit day/month/year validation.
- `DatePicker`, `DateRangePicker`, `MonthYearPicker` and `DateTimePicker` compose the shared Calendar/Popover/Input primitives and remain usable with TanStack Form and Zod.
- Calendar is React DayPicker based, Vietnamese-localized and Monday-first. Min/max and disabled matchers belong to the caller.
- Display formatting is presentation only; domain storage should use `Date` or a documented ISO/timestamp representation.

## Select, Combobox and disclosure
- Select is for small option sets; Radio is for 2–4 visible choices; Combobox is for searchable or large option sets; MultiCombobox is for multiple searchable values.
- Accordion is a structured collection of related disclosure items. Collapsible remains the primitive for one arbitrary disclosure region.
- Dialog is a focused decision/form modal; Sheet is a large desktop side panel; Drawer is a temporary mobile/bottom surface; Popover is a small anchored interaction.

## File upload
`FileUpload` is a frontend-only composition around the native file input. It supports browse, drag/drop, accept/type, size and count UX validation, compact file rows, image previews and caller-controlled progress. It does not upload, call a server or fake progress automatically. `FileUpload` selects/adds files; a future Attachment/FileItem pattern would only display existing files.

## Responsive picker behavior
Date and Combobox popovers are viewport-safe. `ResponsiveDialog` uses Dialog on desktop and Drawer on mobile for short actions without duplicating content state. Existing Sheet usage remains a side panel and is not automatically replaced by Drawer.

## Destructive action rule
Use `ConfirmDialog` only for irreversible or high-impact actions. Delete is destructive; deactivate or archive should use warning/neutral treatment when the action is reversible. Do not add fake Undo actions.

## Shared primitives
- `Textarea` follows the same 14px, 6px radius, border and focus-ring contract as Input and Select.
- `Tabs` use Radix keyboard behavior with flat underline triggers, 14px text and horizontal scrolling on narrow screens.
- `RadioGroup` is for small, mutually exclusive choices where visible labels are useful; do not replace every Select.
- `Alert` supports info, success, warning and destructive contextual feedback without shadow.
- `Progress` is horizontal, 6–8px high, semantic and limited to 0–100 values.
- `EmptyState` is for non-table empty surfaces. It keeps icon, heading, description and optional actions compact.

## Motion and interaction
Motion is functional, not decorative. It explains where an overlay or spatial panel came from, confirms a state change and keeps dismissal responsive.

- Fast: 140ms for hover, color and icon feedback.
- Base: 180ms for dropdowns, popovers, dialogs and collapsible navigation.
- Slow: 240ms for spatial Sheet/drawer transitions.
- Enter uses ease-out; exit uses ease-in. Standard admin interactions stay at or below 300ms.
- Sheet slides from its opening edge. Dialog fades and scales only from approximately 98% to 100%. Dropdown, Popover, Select and Tooltip share a restrained fade/zoom/directional language.
- Do not add route transitions, table-row staggering, bounce/spring motion or a new animation library.
- `prefers-reduced-motion: reduce` reduces animation and transition timing automatically while preserving the state change and Radix focus lifecycle.

## Color
Use semantic tokens: `background`, `foreground`, `card`, `popover`, `primary`, `secondary`, `muted`, `accent`, `border`, `input`, `ring`, plus semantic status colors (`success`, `warning`, `info`, `destructive`). Feature code must not introduce raw hex colors or Tailwind palette classes (`emerald-*`, `blue-*`, `amber-*`, etc.); status dots, progress segments and emphasis text all use semantic tokens.

## Dark mode
Dark mode changes token values, not component implementations.

## Responsive rules

- Page titles are 30px on desktop and 26px on mobile.
- Keep body, controls and navigation at their desktop scale on mobile.
- Table cells may step down to 12px on mobile (`text-xs sm:text-sm`); compact toolbars stay 12px at all breakpoints.
- Prefer layout changes, column hiding or horizontal scrolling over shrinking table text further.
- Test 375px, 390px, 430px, 768px, 1024px, 1280px, 1440px and 1920px.
- Check expanded/collapsed sidebar, overlays, Users toolbar, pagination, dialogs and sheets in light and dark mode.

## Acceptance page
`/design-system` is the visual regression page. Check it before accepting design-system changes.
