import { AlertCircle, Check, ChevronDown, Loader2, X } from "lucide-react";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";

export type ComboboxOption = {
  value: string;
  label: string;
  disabled?: boolean;
};

type ComboboxProps = {
  options: ComboboxOption[];
  value?: string;
  onValueChange?: (value: string | undefined) => void;
  placeholder?: string;
  searchPlaceholder?: string;
  emptyMessage?: string;
  disabled?: boolean;
  loading?: boolean;
  errorMessage?: string;
  clearable?: boolean;
  className?: string;
};

function Combobox({
  options,
  value,
  onValueChange,
  placeholder = "Chọn hoặc tìm kiếm...",
  searchPlaceholder = "Tìm kiếm...",
  emptyMessage = "Không tìm thấy kết quả.",
  disabled,
  loading,
  errorMessage,
  clearable = false,
  className,
}: ComboboxProps) {
  const [open, setOpen] = useState(false);
  const selectedOption = options.find((option) => option.value === value);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <div className="relative">
        <PopoverTrigger asChild>
          <Button
            type="button"
            variant="outline"
            role="combobox"
            aria-expanded={open}
            disabled={disabled}
            className={cn(
              "relative w-full justify-start font-normal",
              clearable ? "pr-16" : "pr-8",
              className,
            )}
          >
            <span
              className={cn(
                "min-w-0 flex-1 truncate text-left",
                !selectedOption && "text-muted-foreground",
              )}
            >
              {selectedOption?.label ?? placeholder}
            </span>
          </Button>
        </PopoverTrigger>
        {clearable && value ? (
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label="Xóa lựa chọn"
            className="absolute top-1/2 right-9 -translate-y-1/2"
            onPointerDown={(event) => event.stopPropagation()}
            onClick={(event) => {
              event.stopPropagation();
              onValueChange?.(undefined);
            }}
          >
            <X />
          </Button>
        ) : null}
        <ChevronDown className="pointer-events-none absolute top-1/2 right-2 size-4 -translate-y-1/2 opacity-50" />
      </div>
      <PopoverContent
        align="start"
        className="w-[var(--radix-popover-trigger-width)] min-w-56 p-0"
      >
        <Command>
          <CommandInput placeholder={searchPlaceholder} />
          <CommandList>
            {loading ? (
              <CommandEmpty>
                <span className="inline-flex items-center gap-2">
                  <Loader2 className="animate-spin" />
                  Đang tải...
                </span>
              </CommandEmpty>
            ) : errorMessage ? (
              <CommandEmpty>
                <span className="inline-flex items-center gap-2 text-destructive">
                  <AlertCircle />
                  {errorMessage}
                </span>
              </CommandEmpty>
            ) : (
              <>
                <CommandEmpty>{emptyMessage}</CommandEmpty>
                <CommandGroup>
                  {options.map((option) => (
                    <CommandItem
                      key={option.value}
                      value={`${option.value} ${option.label}`}
                      disabled={option.disabled}
                      onSelect={() => {
                        onValueChange?.(option.value);
                        setOpen(false);
                      }}
                    >
                      <Check
                        className={cn(
                          "size-4 shrink-0 opacity-0",
                          option.value === value && "opacity-100",
                        )}
                      />
                      <span className="min-w-0 flex-1 truncate">
                        {option.label}
                      </span>
                    </CommandItem>
                  ))}
                </CommandGroup>
              </>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

type MultiComboboxProps = Omit<ComboboxProps, "value" | "onValueChange"> & {
  value?: string[];
  onValueChange?: (value: string[]) => void;
  maxVisible?: number;
};

function MultiCombobox({
  options,
  value = [],
  onValueChange,
  placeholder = "Chọn nhiều giá trị...",
  searchPlaceholder = "Tìm kiếm...",
  emptyMessage = "Không tìm thấy kết quả.",
  disabled,
  loading,
  errorMessage,
  maxVisible = 2,
  className,
}: MultiComboboxProps) {
  const [open, setOpen] = useState(false);
  const selectedOptions = useMemo(
    () =>
      value
        .map((item) => options.find((option) => option.value === item))
        .filter(Boolean) as ComboboxOption[],
    [options, value],
  );
  const visibleOptions = selectedOptions.slice(0, maxVisible);
  const hiddenCount = selectedOptions.length - visibleOptions.length;

  const toggleValue = (nextValue: string) => {
    onValueChange?.(
      value.includes(nextValue)
        ? value.filter((item) => item !== nextValue)
        : [...value, nextValue],
    );
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          role="combobox"
          aria-expanded={open}
          disabled={disabled}
          className={cn(
            "relative min-h-[var(--control-height)] w-full justify-start pr-10 font-normal",
            className,
          )}
        >
          {visibleOptions.length > 0 ? (
            <span className="flex min-w-0 max-h-7 flex-1 flex-wrap items-center gap-1 overflow-hidden">
              {visibleOptions.map((option) => (
                <span
                  key={option.value}
                  className="max-w-32 truncate rounded-sm bg-muted px-1.5 py-0.5 text-xs"
                >
                  {option.label}
                </span>
              ))}
              {hiddenCount > 0 ? (
                <span className="text-xs text-muted-foreground">
                  +{hiddenCount}
                </span>
              ) : null}
            </span>
          ) : (
            <span className="min-w-0 flex-1 truncate text-left text-muted-foreground">
              {placeholder}
            </span>
          )}
          <ChevronDown className="pointer-events-none absolute top-1/2 right-2 size-4 -translate-y-1/2 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent
        align="start"
        className="w-[var(--radix-popover-trigger-width)] min-w-56 p-0"
      >
        <Command>
          <CommandInput placeholder={searchPlaceholder} />
          <CommandList>
            {loading ? (
              <CommandEmpty>Đang tải...</CommandEmpty>
            ) : errorMessage ? (
              <CommandEmpty className="text-destructive">
                {errorMessage}
              </CommandEmpty>
            ) : (
              <>
                <CommandEmpty>{emptyMessage}</CommandEmpty>
                <CommandGroup>
                  {options.map((option) => (
                    <CommandItem
                      key={option.value}
                      value={`${option.value} ${option.label}`}
                      disabled={option.disabled}
                      onSelect={() => toggleValue(option.value)}
                    >
                      <Check
                        className={cn(
                          "size-4 shrink-0 opacity-0",
                          value.includes(option.value) && "opacity-100",
                        )}
                      />
                      <span className="min-w-0 flex-1 truncate">
                        {option.label}
                      </span>
                    </CommandItem>
                  ))}
                </CommandGroup>
              </>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

export { Combobox, MultiCombobox };
