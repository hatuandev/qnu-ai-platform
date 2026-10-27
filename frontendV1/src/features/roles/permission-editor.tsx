import { Check, ChevronDown, Eraser } from "lucide-react";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import {
  type PermissionCatalogItem,
  type PermissionKey,
  permissionCatalog,
} from "@/rbac/catalog";

type PermissionGroup = {
  resource: string;
  label: string;
  items: PermissionCatalogItem[];
};

const permissionGroups = permissionCatalog.reduce<PermissionGroup[]>(
  (groups, permission) => {
    const current = groups.find(
      (group) => group.resource === permission.resource,
    );
    if (current) current.items.push(permission);
    else {
      groups.push({
        resource: permission.resource,
        label: permission.resourceLabel,
        items: [permission],
      });
    }
    return groups;
  },
  [],
);

export function getPermissionGroups() {
  return permissionGroups;
}

export function PermissionEditor({
  value,
  onChange,
  disabled = false,
  compact = false,
}: {
  value: PermissionKey[];
  onChange: (value: PermissionKey[]) => void;
  disabled?: boolean;
  compact?: boolean;
}) {
  const [query, setQuery] = useState("");
  const selected = useMemo(() => new Set(value), [value]);
  const normalizedQuery = query.trim().toLowerCase();
  const visibleGroups = useMemo(
    () =>
      permissionGroups
        .map((group) => ({
          ...group,
          items: group.items.filter((permission) => {
            if (!normalizedQuery) return true;
            return [
              permission.label,
              permission.key,
              permission.description,
              permission.resource,
              permission.resourceLabel,
            ].some((part) => part.toLowerCase().includes(normalizedQuery));
          }),
        }))
        .filter((group) => group.items.length > 0),
    [normalizedQuery],
  );
  const updateGroup = (group: PermissionGroup, checked: boolean) => {
    const next = new Set(value);
    for (const permission of group.items) {
      if (checked) next.add(permission.key);
      else next.delete(permission.key);
    }
    onChange([...next]);
  };
  const allVisibleKeys = visibleGroups.flatMap((group) =>
    group.items.map((permission) => permission.key),
  );
  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <Input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Tìm kiếm quyền hạn..."
          aria-label="Tìm kiếm quyền hạn"
          className="sm:max-w-sm"
          disabled={disabled}
        />
        <div className="flex flex-wrap items-center gap-1 sm:ml-auto">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            disabled={disabled || allVisibleKeys.length === 0}
            onClick={() =>
              updateGroup(
                {
                  resource: "visible",
                  label: "",
                  items: visibleGroups.flatMap((group) => group.items),
                },
                true,
              )
            }
          >
            <Check />
            Chọn tất cả
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            disabled={disabled || allVisibleKeys.length === 0}
            onClick={() =>
              updateGroup(
                {
                  resource: "visible",
                  label: "",
                  items: visibleGroups.flatMap((group) => group.items),
                },
                false,
              )
            }
          >
            <Eraser />
            Bỏ chọn
          </Button>
        </div>
      </div>
      {visibleGroups.length ? (
        <div className={compact ? "space-y-4" : "grid gap-4 md:grid-cols-2"}>
          {visibleGroups.map((group) => {
            const groupKeys = group.items.map((permission) => permission.key);
            const groupSelected = groupKeys.filter((key) =>
              selected.has(key),
            ).length;
            const allSelected = groupSelected === groupKeys.length;
            return (
              <section
                key={group.resource}
                className="rounded-md border bg-card"
              >
                <div className="flex items-center justify-between gap-3 border-b px-3 py-2.5">
                  <div className="min-w-0">
                    <h3 className="text-sm font-semibold">{group.label}</h3>
                    <p className="text-xs text-muted-foreground">
                      {groupSelected}/{groupKeys.length} quyền đã chọn
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="shrink-0"
                    aria-label={`${allSelected ? "Bỏ chọn" : "Chọn"} tất cả quyền ${group.label}`}
                    disabled={disabled}
                    onClick={() => updateGroup(group, !allSelected)}
                  >
                    <ChevronDown
                      className={allSelected ? "rotate-180" : undefined}
                    />
                    {allSelected ? "Bỏ chọn" : "Chọn tất cả"}
                  </Button>
                </div>
                <div className="divide-y">
                  {group.items.map((permission) => {
                    const inputId = `permission-${permission.key.replace(".", "-")}`;
                    return (
                      <label
                        key={permission.key}
                        htmlFor={inputId}
                        className="flex min-h-14 cursor-pointer items-start gap-3 px-3 py-2.5 hover:bg-muted/40"
                      >
                        <Checkbox
                          id={inputId}
                          checked={selected.has(permission.key)}
                          disabled={disabled}
                          onCheckedChange={(checked) => {
                            const next = new Set(value);
                            if (checked) next.add(permission.key);
                            else next.delete(permission.key);
                            onChange([...next]);
                          }}
                          className="mt-0.5"
                        />
                        <span className="min-w-0">
                          <span className="block text-sm font-medium">
                            {permission.label}
                          </span>
                          <span className="block text-xs text-muted-foreground">
                            {permission.description}
                          </span>
                          <span className="type-metadata font-mono text-muted-foreground">
                            {permission.key}
                          </span>
                        </span>
                      </label>
                    );
                  })}
                </div>
              </section>
            );
          })}
        </div>
      ) : (
        <div className="rounded-md border border-dashed px-4 py-8 text-center text-sm text-muted-foreground">
          Không tìm thấy quyền hạn phù hợp.
        </div>
      )}
      <Separator />
    </div>
  );
}
