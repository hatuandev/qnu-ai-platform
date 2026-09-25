import type { LucideIcon } from "lucide-react";

export type AppPath =
  | "/dashboard"
  | "/"
  | "/assistants"
  | "/knowledge"
  | "/models"
  | "/conversations"
  | "/quality"
  | "/runs"
  | "/operations/runs"
  | "/settings/integrations"
  | "/capabilities/nodes"
  | "/capabilities/tools"
  | "/document-types"
  | "/knowledge/settings/document-types"
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
  | "/help";

export type NavItem = {
  id: string;
  title: string;
  to?: AppPath;
  icon?: LucideIcon;
  permission?: string;
  audience?: "all" | "student" | "staff";
  badge?: string | number;
  children?: NavItem[];
};

export type NavGroup = { id: string; label: string; items: NavItem[] };
