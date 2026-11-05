import { Link } from "@tanstack/react-router";
import type { LucideIcon } from "lucide-react";
import { Fragment, type ReactNode } from "react";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

export type PageBreadcrumbItem = {
  /** Nhãn hiển thị của mục */
  label: string;
  /** Đường dẫn TanStack Router */
  to?: string;
  /** Tham số path (params) */
  params?: Record<string, string>;
  /** Tham số query search */
  search?: Record<string, unknown>;
  /** Icon Lucide đại diện cho cấp bậc (tùy chọn) */
  icon?: LucideIcon;
  /** Đánh dấu mục hiện tại (mặc định mục cuối cùng là current) */
  current?: boolean;
  /** Giới hạn số ký tự trước khi cắt ngắn (mặc định 28) */
  maxChars?: number;
  /** Badge kèm theo nếu có (ví dụ: Gen #1, v1) */
  badge?: ReactNode;
  /** Sự kiện click tùy biến */
  onClick?: () => void;
};

export type PageBreadcrumbsProps = {
  items: PageBreadcrumbItem[];
  className?: string;
  ariaLabel?: string;
  separator?: ReactNode;
};

export function PageBreadcrumbs({
  items,
  className,
  ariaLabel = "Điều hướng đường dẫn",
  separator,
}: PageBreadcrumbsProps) {
  if (!items || items.length === 0) return null;

  return (
    <TooltipProvider delayDuration={300}>
      <Breadcrumb
        aria-label={ariaLabel}
        className={cn("type-supporting py-0.5", className)}
      >
        <BreadcrumbList className="gap-1 sm:gap-1.5">
          {items.map((item, index) => {
            const isLast = index === items.length - 1;
            const isCurrent = item.current ?? isLast;
            const Icon = item.icon;
            const maxChars = item.maxChars ?? 28;
            const isLong = item.label.length > maxChars;

            // Nội dung nhãn (có icon và badge)
            const labelNode = (
              <span className="inline-flex items-center gap-1.5 min-w-0">
                {Icon ? (
                  <Icon
                    className={cn(
                      "size-3.5 shrink-0 transition-colors",
                      isCurrent
                        ? "text-primary"
                        : "text-muted-foreground/70 group-hover:text-primary",
                    )}
                    aria-hidden="true"
                  />
                ) : null}
                <span
                  className={cn(
                    "truncate inline-block transition-colors",
                    isLong
                      ? "max-w-[140px] sm:max-w-[200px] md:max-w-[260px]"
                      : "max-w-[320px]",
                  )}
                >
                  {item.label}
                </span>
                {item.badge}
              </span>
            );

            // Bọc Tooltip nếu tên quá dài
            const wrappedNode = isLong ? (
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="inline-flex items-center cursor-default">
                    {labelNode}
                  </span>
                </TooltipTrigger>
                <TooltipContent side="bottom" align="start">
                  {item.label}
                </TooltipContent>
              </Tooltip>
            ) : (
              labelNode
            );

            return (
              <Fragment key={`${item.label}-${index}`}>
                <BreadcrumbItem>
                  {isCurrent || !item.to ? (
                    <BreadcrumbPage
                      className={cn(
                        "group font-medium inline-flex items-center gap-1.5",
                        isCurrent && "font-semibold text-foreground",
                      )}
                    >
                      {wrappedNode}
                    </BreadcrumbPage>
                  ) : (
                    <BreadcrumbLink asChild>
                      <Link
                        to={item.to as unknown as string}
                        params={item.params}
                        search={item.search}
                        onClick={item.onClick}
                        className="group inline-flex items-center gap-1.5 text-muted-foreground hover:text-primary transition-colors py-0.5"
                      >
                        {wrappedNode}
                      </Link>
                    </BreadcrumbLink>
                  )}
                </BreadcrumbItem>

                {!isLast ? (
                  <BreadcrumbSeparator>{separator}</BreadcrumbSeparator>
                ) : null}
              </Fragment>
            );
          })}
        </BreadcrumbList>
      </Breadcrumb>
    </TooltipProvider>
  );
}
