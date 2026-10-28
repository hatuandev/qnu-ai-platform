import type { LucideIcon } from "lucide-react";

export type AppPath =
  | "/dashboard"
  | "/reference-dashboard"
  | "/users"
  | "/users/invitations"
  | "/roles"
  | "/permissions"
  | "/buildings"
  | "/floors"
  | "/room-types"
  | "/rooms"
  | "/academic-years"
  | "/registration-periods"
  | "/priority-objects"
  | "/difficult-areas"
  | "/applications"
  | "/students"
  | "/student/register"
  | "/student/room-selection"
  | "/student/registration-history"
  | "/student/payments"
  | "/notifications"
  | "/support"
  | "/assignments"
  | "/residences"
  | "/residence-contracts"
  | "/invoices"
  | "/payment-submissions"
  | "/payment-configurations"
  | "/debts"
  | "/fee-rates"
  | "/reports"
  | "/activity"
  | "/analytics"
  | "/settings"
  | "/settings/notifications"
  | "/settings/security"
  | "/profile"
  | "/design-system"
  | "/help"
  // QNU AI v1 (real backendV1 data)
  | "/workspaces"
  | "/modelops/providers"
  | "/modelops/endpoints"
  | "/modelops/defaults"
  | "/modelops/events";

/**
 * `v1` items are gated by backendV1 permissions and the v1 session; the default
 * scope is the copied KTX template, whose permissions must never unlock v1.
 */
export type NavScope = "ktx" | "v1";

export type NavItem = {
  id: string;
  title: string;
  to?: AppPath;
  icon?: LucideIcon;
  permission?: string;
  audience?: "all" | "student" | "staff";
  badge?: string | number;
  scope?: NavScope;
  children?: NavItem[];
};

export type NavGroup = {
  id: string;
  label: string;
  items: NavItem[];
  /** Rendered with a "Mẫu" chip so template sections stay unmistakable. */
  template?: boolean;
};
