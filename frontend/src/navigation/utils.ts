import { hiddenRouteMeta, navigationGroups } from "@/navigation/config";
import type { NavGroup, NavItem } from "@/navigation/types";
import { isStudentAccount } from "@/rbac/backend-role-map";

export function filterNavigationGroups(
  groups: NavGroup[],
  can: (permission?: string) => boolean,
  userType?: string,
): NavGroup[] {
  return groups
    .map((group) => ({
      ...group,
      items: group.items
        .map((item) => filterItem(item, can, userType))
        .filter(Boolean) as NavItem[],
    }))
    .filter((group) => group.items.length > 0);
}

function filterItem(
  item: NavItem,
  can: (permission?: string) => boolean,
  userType?: string,
): NavItem | null {
  const isStudent = isStudentAccount(userType);
  if (item.audience === "student" && !isStudent) return null;
  if (item.audience === "staff" && isStudent) return null;
  if (!can(item.permission)) return null;
  const children = item.children
    ?.map((child) => filterItem(child, can, userType))
    .filter(Boolean) as NavItem[] | undefined;
  if (item.children && (!children || children.length === 0) && !item.to)
    return null;
  return { ...item, children };
}

export function flattenNavigation(groups = navigationGroups): NavItem[] {
  const output: NavItem[] = [];
  for (const group of groups)
    for (const item of group.items) {
      if (item.to) output.push(item);
      if (item.children)
        output.push(...item.children.filter((child) => child.to));
    }
  return output;
}

export function isItemActive(item: NavItem, pathname: string): boolean {
  if (item.to && pathname === item.to) return true;
  return item.children?.some((child) => child.to === pathname) ?? false;
}

type BreadcrumbItem = { label: string };

function withoutDuplicateLabels(items: BreadcrumbItem[]): BreadcrumbItem[] {
  const seen = new Set<string>();
  return items.filter((item) => {
    if (seen.has(item.label)) return false;
    seen.add(item.label);
    return true;
  });
}

export function getBreadcrumbs(pathname: string) {
  if (pathname.startsWith("/buildings/")) {
    return [
      { label: "Ký túc xá" },
      { label: "Tòa nhà" },
      { label: "Chi tiết" },
    ];
  }
  if (pathname.startsWith("/floors/")) {
    return [{ label: "Ký túc xá" }, { label: "Tầng" }, { label: "Chi tiết" }];
  }
  const studentRouteBreadcrumbs: Record<string, BreadcrumbItem[]> = {
    "/dashboard": [{ label: "Trang chủ" }, { label: "Tổng quan" }],
    "/student/register": [
      { label: "Trang chủ" },
      { label: "Không gian sinh viên" },
      { label: "Đăng ký phòng" },
    ],
    "/student/registration-history": [
      { label: "Trang chủ" },
      { label: "Không gian sinh viên" },
      { label: "Lịch sử đăng ký" },
    ],
    "/student/room-selection": [
      { label: "Trang chủ" },
      { label: "Không gian sinh viên" },
      { label: "Chọn phòng" },
    ],
    "/student/payments": [
      { label: "Trang chủ" },
      { label: "Không gian sinh viên" },
      { label: "Thanh toán" },
    ],
  };
  const studentBreadcrumbs = studentRouteBreadcrumbs[pathname];
  if (studentBreadcrumbs) return studentBreadcrumbs;

  for (const group of navigationGroups) {
    for (const item of group.items) {
      if (item.to === pathname)
        return withoutDuplicateLabels([
          { label: group.label },
          { label: item.title },
        ]);
      const child = item.children?.find(
        (candidate) => candidate.to === pathname,
      );
      if (child)
        return withoutDuplicateLabels([
          { label: group.label },
          { label: item.title },
          { label: child.title },
        ]);
    }
  }
  const hidden = hiddenRouteMeta.find((item) => item.to === pathname);
  return hidden ? [{ label: hidden.title }] : [{ label: "Quản trị" }];
}
