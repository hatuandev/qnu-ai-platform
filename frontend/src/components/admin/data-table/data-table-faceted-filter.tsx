import { Check, Plus } from "lucide-react";
import type { ComponentType } from "react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";

export type DataTableFacetOption = {
  value: string;
  label: string;
  count?: number;
  icon?: ComponentType<{ className?: string }>;
};

export function DataTableFacetedFilter({
  title,
  options,
  selectedValues,
  onChange,
}: {
  title: string;
  options: DataTableFacetOption[];
  selectedValues: string[];
  onChange: (values: string[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const selected = new Set(selectedValues);
  const toggle = (value: string) =>
    onChange(
      selected.has(value)
        ? selectedValues.filter((item) => item !== value)
        : [...selectedValues, value],
    );
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" className="h-8 border-dashed">
          <Plus className="size-3.5" />
          {title}
          {selectedValues.length ? (
            <>
              <span className="mx-1 h-4 w-px bg-border" />
              <Badge
                variant="secondary"
                className="rounded-sm px-1.5 font-normal"
              >
                {selectedValues.length}
              </Badge>
            </>
          ) : null}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-[240px] p-0">
        <Command>
          <CommandInput placeholder={`Lọc ${title.toLowerCase()}...`} />
          <CommandList>
            <CommandEmpty>Không tìm thấy {title.toLowerCase()}.</CommandEmpty>
            <CommandGroup heading={title}>
              {options.map((option) => {
                const Icon = option.icon;
                return (
                  <CommandItem
                    key={option.value}
                    onSelect={() => toggle(option.value)}
                    className="gap-2"
                  >
                    <span
                      className={cn(
                        "flex size-4 shrink-0 items-center justify-center rounded-sm border",
                        selected.has(option.value) &&
                          "border-primary bg-primary text-primary-foreground",
                      )}
                    >
                      {selected.has(option.value) ? (
                        <Check className="size-3" />
                      ) : null}
                    </span>
                    {Icon ? (
                      <Icon className="size-4 text-muted-foreground" />
                    ) : null}
                    <span className="min-w-0 flex-1 truncate">
                      {option.label}
                    </span>
                    {option.count !== undefined ? (
                      <span className="ml-auto text-xs text-muted-foreground">
                        {option.count}
                      </span>
                    ) : null}
                  </CommandItem>
                );
              })}
            </CommandGroup>
            {selectedValues.length ? (
              <>
                <CommandSeparator />
                <CommandItem
                  onSelect={() => onChange([])}
                  className="justify-center"
                >
                  Xóa bộ lọc
                </CommandItem>
              </>
            ) : null}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
