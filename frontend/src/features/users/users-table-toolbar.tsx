import { RotateCcw } from "lucide-react";
import type { ReactNode } from "react";
import {
  DataTableFacetedFilter,
  type DataTableFacetOption,
} from "@/components/admin/data-table/data-table-faceted-filter";
import { DebouncedSearchInput } from "@/components/admin/debounced-search-input";
import { Button } from "@/components/ui/button";

export function UsersTableToolbar({
  query,
  roleOptions,
  statusOptions,
  selectedRoles,
  selectedStatuses,
  hasActiveFilters,
  viewOptions,
  onQueryChange,
  onRolesChange,
  onStatusesChange,
  onReset,
}: {
  query: string;
  roleOptions: DataTableFacetOption[];
  statusOptions: DataTableFacetOption[];
  selectedRoles: string[];
  selectedStatuses: string[];
  hasActiveFilters: boolean;
  viewOptions: ReactNode;
  onQueryChange: (value: string) => void;
  onRolesChange: (values: string[]) => void;
  onStatusesChange: (values: string[]) => void;
  onReset: () => void;
}) {
  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
      <div className="w-full sm:w-[320px]">
        <DebouncedSearchInput
          value={query}
          onChange={onQueryChange}
          placeholder="Tìm theo tên hoặc email..."
          aria-label="Tìm kiếm người dùng"
        />
      </div>
      <DataTableFacetedFilter
        title="Vai trò"
        options={roleOptions}
        selectedValues={selectedRoles}
        onChange={onRolesChange}
      />
      <DataTableFacetedFilter
        title="Trạng thái"
        options={statusOptions}
        selectedValues={selectedStatuses}
        onChange={onStatusesChange}
      />
      {hasActiveFilters ? (
        <Button variant="ghost" size="sm" onClick={onReset}>
          <RotateCcw />
          Đặt lại
        </Button>
      ) : null}
      <div className="sm:ml-auto">{viewOptions}</div>
    </div>
  );
}
