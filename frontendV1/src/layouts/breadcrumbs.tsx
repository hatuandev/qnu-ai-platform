import { useRouterState } from "@tanstack/react-router";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { getBreadcrumbs } from "@/navigation/utils";

export function Breadcrumbs() {
  const location = useRouterState({ select: (state) => state.location });
  const items = getBreadcrumbs(location.pathname, location.search);

  return (
    <Breadcrumb aria-label="Điều hướng đường dẫn" className="hidden min-w-0 md:block">
      <BreadcrumbList className="type-supporting m-0 flex list-none items-center gap-1.5 p-0 text-muted-foreground">
        {items.map((item, index) => {
          const isLast = index === items.length - 1;
          return (
            <span key={item.label} className="inline-flex items-center gap-1.5 min-w-0">
              {index > 0 ? <BreadcrumbSeparator /> : null}
              <BreadcrumbItem>
                <BreadcrumbPage
                  className={
                    isLast
                      ? "truncate font-medium text-foreground"
                      : "truncate text-muted-foreground"
                  }
                  aria-current={isLast ? "page" : undefined}
                >
                  {item.label}
                </BreadcrumbPage>
              </BreadcrumbItem>
            </span>
          );
        })}
      </BreadcrumbList>
    </Breadcrumb>
  );
}
