import { Link, useLocation } from "@tanstack/react-router";
import { Fragment } from "react";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { useUiStore } from "@/lib/ui-store";

type BreadcrumbEntry = {
  label: string;
  to?: string;
};

function getRouteCrumbs(
  pathname: string,
  workspaceName?: string,
): BreadcrumbEntry[] {
  const rootLabel = workspaceName || "QNU AI Platform";
  const crumbs: BreadcrumbEntry[] = [{ label: rootLabel, to: "/dashboard" }];

  if (pathname === "/dashboard" || pathname === "") {
    crumbs.push({ label: "Tổng quan" });
    return crumbs;
  }

  if (pathname.startsWith("/knowledge")) {
    crumbs.push({ label: "Kho tri thức", to: "/knowledge" });

    if (pathname !== "/knowledge") {
      crumbs.push({ label: "Chi tiết tài liệu" });
    }
    return crumbs;
  }

  if (pathname.startsWith("/assistants")) {
    crumbs.push({ label: "Trợ lý AI" });
    return crumbs;
  }

  if (pathname.startsWith("/chat")) {
    crumbs.push({ label: "Hội thoại & RAG" });
    return crumbs;
  }

  if (pathname.startsWith("/operations")) {
    crumbs.push({ label: "Tác vụ & Vận hành" });
    return crumbs;
  }

  if (pathname.startsWith("/modelops")) {
    crumbs.push({ label: "Nhà cung cấp" });
    return crumbs;
  }

  if (pathname.startsWith("/settings")) {
    crumbs.push({ label: "Cài đặt" });
    return crumbs;
  }

  // Fallback for any other path
  const segments = pathname.split("/").filter(Boolean);
  for (let i = 0; i < segments.length; i++) {
    const segment = segments[i];
    const to = `/${segments.slice(0, i + 1).join("/")}`;
    crumbs.push({
      label: segment.charAt(0).toUpperCase() + segment.slice(1),
      to: i < segments.length - 1 ? to : undefined,
    });
  }

  return crumbs;
}

export function AppBreadcrumb() {
  const { pathname } = useLocation();
  const activeWorkspace = useUiStore((s) => s.activeWorkspace);
  const crumbs = getRouteCrumbs(pathname, activeWorkspace?.name);

  return (
    <Breadcrumb className="min-w-0">
      <BreadcrumbList className="gap-1.5 sm:gap-2 text-xs">
        {crumbs.map((crumb, index) => {
          const isLast = index === crumbs.length - 1;

          return (
            <Fragment
              key={crumb.to ? `link-${crumb.to}` : `page-${crumb.label}`}
            >
              <BreadcrumbItem
                className={isLast ? "min-w-0" : "hidden md:inline-flex"}
              >
                {isLast || !crumb.to ? (
                  <BreadcrumbPage className="font-semibold text-foreground truncate max-w-[200px] sm:max-w-[320px]">
                    {crumb.label}
                  </BreadcrumbPage>
                ) : (
                  <BreadcrumbLink asChild>
                    <Link
                      to={crumb.to}
                      className="text-muted-foreground hover:text-primary transition-colors truncate max-w-[160px] sm:max-w-[240px]"
                    >
                      {crumb.label}
                    </Link>
                  </BreadcrumbLink>
                )}
              </BreadcrumbItem>

              {!isLast && (
                <BreadcrumbSeparator className="hidden md:inline-flex text-muted-foreground/40">
                  /
                </BreadcrumbSeparator>
              )}
            </Fragment>
          );
        })}
      </BreadcrumbList>
    </Breadcrumb>
  );
}
