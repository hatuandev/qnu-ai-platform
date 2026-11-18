import { ChevronsUpDown, Database } from "lucide-react";
import { useMemo, useState } from "react";
import type { AssistantReadiness } from "@/api/assistants";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { MAX_COLLECTIONS } from "./assistant-form-state";
import { READINESS_MAP } from "./readiness";

export type CollectionOption = {
  id: string;
  name: string;
  source_count: number;
};

export function AssistantCollectionPicker({
  collections,
  selectedIds,
  onChange,
  disabled = false,
  readiness,
}: {
  collections: CollectionOption[];
  selectedIds: string[];
  onChange: (ids: string[]) => void;
  disabled?: boolean;
  readiness?: AssistantReadiness;
}) {
  const [open, setOpen] = useState(false);
  const selected = useMemo(() => new Set(selectedIds), [selectedIds]);
  const readinessById = useMemo(
    () =>
      new Map(
        (readiness?.collections ?? []).map((item) => [
          item.collection_id,
          item,
        ]),
      ),
    [readiness],
  );

  const triggerLabel =
    selectedIds.length === 0
      ? "Chọn kho tri thức"
      : selectedIds.length === 1
        ? (collections.find((item) => item.id === selectedIds[0])?.name ??
          "1 kho tri thức")
        : `${selectedIds.length} kho tri thức`;

  const toggle = (collectionId: string) => {
    if (selected.has(collectionId)) {
      onChange(selectedIds.filter((item) => item !== collectionId));
      return;
    }
    if (selectedIds.length >= MAX_COLLECTIONS) return;
    onChange([...selectedIds, collectionId]);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          aria-expanded={open}
          disabled={disabled}
          className="h-9 w-full justify-between gap-2 bg-background px-2.5 text-xs font-normal"
        >
          <span className="flex min-w-0 items-center gap-1.5">
            <Database className="size-3.5 shrink-0 text-muted-foreground" />
            <span
              className={cn(
                "truncate",
                selectedIds.length === 0
                  ? "text-muted-foreground"
                  : "text-foreground",
              )}
            >
              {triggerLabel}
            </span>
          </span>
          <ChevronsUpDown className="size-3.5 shrink-0 text-muted-foreground" />
        </Button>
      </PopoverTrigger>
      <PopoverContent
        align="start"
        sideOffset={4}
        className="w-[var(--radix-popover-trigger-width)] min-w-72 p-0"
      >
        <div className="flex items-center justify-between border-b border-border/60 px-3 py-2">
          <span className="text-[11px] font-medium text-muted-foreground">
            Đã chọn {selectedIds.length}/{MAX_COLLECTIONS} kho
          </span>
        </div>
        <div className="max-h-64 overflow-y-auto p-1">
          {collections.length === 0 ? (
            <p className="px-2 py-3 text-[11px] text-muted-foreground">
              Chưa có kho tri thức nào trong đơn vị.
            </p>
          ) : (
            collections.map((collection) => {
              const isSelected = selected.has(collection.id);
              const isAtLimit =
                !isSelected && selectedIds.length >= MAX_COLLECTIONS;
              const collectionReadiness = readinessById.get(collection.id);
              return (
                <label
                  key={collection.id}
                  htmlFor={`assistant-collection-${collection.id}`}
                  className={cn(
                    "flex cursor-pointer items-start gap-2 rounded-md px-2 py-1.5 transition-colors hover:bg-muted/50",
                    isAtLimit && "cursor-not-allowed opacity-50",
                  )}
                >
                  <Checkbox
                    id={`assistant-collection-${collection.id}`}
                    checked={isSelected}
                    disabled={disabled || isAtLimit}
                    onCheckedChange={() => toggle(collection.id)}
                    className="mt-0.5"
                  />
                  <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                    <span className="truncate text-xs font-medium text-foreground">
                      {collection.name}
                    </span>
                    <span className="text-[11px] text-muted-foreground">
                      {collection.source_count} nguồn
                    </span>
                  </span>
                  {collectionReadiness ? (
                    <Badge
                      variant={
                        READINESS_MAP[collectionReadiness.status].variant
                      }
                      className="h-5 shrink-0 px-1.5 text-[10px] font-normal"
                    >
                      {READINESS_MAP[collectionReadiness.status].label}
                    </Badge>
                  ) : null}
                </label>
              );
            })
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}
