import type { Column } from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ChevronsUpDown } from "lucide-react";
import { Button } from "@/components/ui/button";

export function DataTableColumnHeader<TData>({
  column,
  title,
}: {
  column: Column<TData, unknown>;
  title: string;
}) {
  if (!column.getCanSort()) return <span>{title}</span>;
  const state = column.getIsSorted();
  return (
    <Button
      variant="ghost"
      size="sm"
      className="type-table-header -ml-2 h-8 px-2 font-semibold text-muted-foreground"
      onClick={() => column.toggleSorting(state === "asc")}
    >
      {title}
      {state === "desc" ? (
        <ArrowDown />
      ) : state === "asc" ? (
        <ArrowUp />
      ) : (
        <ChevronsUpDown className="opacity-50" />
      )}
    </Button>
  );
}
