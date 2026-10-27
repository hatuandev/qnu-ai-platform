import { useRouterState } from "@tanstack/react-router";
import { ChevronRight } from "lucide-react";
import { getBreadcrumbs } from "@/navigation/utils";

export function Breadcrumbs() {
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  });
  const items = getBreadcrumbs(pathname);

  return (
    <nav aria-label="Điều hướng đường dẫn" className="hidden min-w-0 md:block">
      <ol className="type-supporting m-0 flex list-none items-center gap-1.5 p-0 text-muted-foreground">
        {items.map((item, index) => (
          <li key={item.label} className="flex min-w-0 items-center gap-1.5">
            {index > 0 ? (
              <ChevronRight
                className="size-3.5 shrink-0 text-muted-foreground"
                aria-hidden="true"
              />
            ) : null}
            <span
              className={
                index === items.length - 1
                  ? "truncate font-medium text-foreground"
                  : "truncate"
              }
              aria-current={index === items.length - 1 ? "page" : undefined}
            >
              {item.label}
            </span>
          </li>
        ))}
      </ol>
    </nav>
  );
}
