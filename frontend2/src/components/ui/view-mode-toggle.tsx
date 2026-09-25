import { LayoutGrid, List } from "lucide-react";
import type * as React from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type ViewMode = "grid" | "table" | "list";

export interface ViewModeToggleProps {
  value: ViewMode;
  onChange: (value: "grid" | "table") => void;
  className?: string;
  gridTitle?: string;
  tableTitle?: string;
  disabled?: boolean;
}

/**
 * Standard ViewModeToggle component for switching between Grid (Card) and Table (List) views.
 * Unified across all pages (Document Types, Assistants, Knowledge, Capability Nodes).
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
  const isTable = value === "table" || value === "list";

  return (
    <div
      className={cn(
        "flex items-center gap-1 border border-border rounded-md p-0.5 bg-muted/30 shrink-0",
        className,
      )}
    >
      <Button
        type="button"
        variant={isGrid ? "secondary" : "ghost"}
        size="sm"
        className="h-7 w-7 p-0"
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
        className="h-7 w-7 p-0"
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
