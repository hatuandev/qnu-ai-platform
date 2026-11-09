import { LayoutGrid, List } from "lucide-react";
import type * as React from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type ViewMode = "grid" | "table";

export interface ViewModeToggleProps {
  value: ViewMode;
  onChange: (value: ViewMode) => void;
  className?: string;
  gridTitle?: string;
  tableTitle?: string;
  disabled?: boolean;
}

/**
 * ViewModeToggle component for switching between Grid (Card) and Table (List) views.
 * Adheres to Academic Teal design tokens and accessible ARIA attributes.
 */
export const ViewModeToggle: React.FC<ViewModeToggleProps> = ({
  value,
  onChange,
  className,
  gridTitle = "Xem dạng thẻ lưới",
  tableTitle = "Xem dạng danh sách bảng",
  disabled = false,
}) => {
  const isGrid = value === "grid";
  const isTable = value === "table";

  return (
    <div
      className={cn(
        "flex items-center gap-1 border border-border rounded-lg p-0.5 bg-muted/30 shrink-0",
        className,
      )}
    >
      <Button
        type="button"
        variant={isGrid ? "secondary" : "ghost"}
        size="sm"
        className={cn(
          "h-7 w-7 p-0 rounded-md transition-colors",
          isGrid && "bg-background shadow-2xs font-semibold text-foreground",
        )}
        onClick={() => onChange("grid")}
        disabled={disabled}
        title={gridTitle}
        aria-label={gridTitle}
        aria-pressed={isGrid}
      >
        <LayoutGrid className="size-3.5" />
      </Button>
      <Button
        type="button"
        variant={isTable ? "secondary" : "ghost"}
        size="sm"
        className={cn(
          "h-7 w-7 p-0 rounded-md transition-colors",
          isTable && "bg-background shadow-2xs font-semibold text-foreground",
        )}
        onClick={() => onChange("table")}
        disabled={disabled}
        title={tableTitle}
        aria-label={tableTitle}
        aria-pressed={isTable}
      >
        <List className="size-3.5" />
      </Button>
    </div>
  );
};
