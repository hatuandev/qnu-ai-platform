import { format, isValid, parseISO } from "date-fns";
import { Calendar as CalendarIcon, X } from "lucide-react";
import * as React from "react";
import { Calendar } from "@/components/ui/calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";

export interface DatePickerProps {
  value?: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  id?: string;
}

export function DatePicker({
  value,
  onChange,
  placeholder = "Không giới hạn",
  disabled,
  className,
  id,
}: DatePickerProps) {
  const [open, setOpen] = React.useState(false);

  const selectedDate = React.useMemo(() => {
    if (!value || typeof value !== "string" || !value.trim()) return null;
    const parsed = parseISO(value);
    return isValid(parsed) ? parsed : null;
  }, [value]);

  const handleSelect = (date: Date | null) => {
    if (date && isValid(date)) {
      onChange(format(date, "yyyy-MM-dd"));
    } else {
      onChange("");
    }
    setOpen(false);
  };

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    onChange("");
    setOpen(false);
  };

  return (
    <div className={cn("relative flex w-full items-center", className)}>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <button
            id={id}
            type="button"
            disabled={disabled}
            className={cn(
              "type-control flex h-9 w-full items-center justify-between gap-2 rounded-md border border-input bg-background px-3 text-xs text-left transition-colors select-none",
              "hover:border-primary/50 focus-visible:outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/20",
              !selectedDate && "text-muted-foreground",
              selectedDate && "font-medium text-foreground",
              selectedDate && !disabled && "pr-8",
              disabled &&
                "cursor-not-allowed opacity-50 bg-muted/40 pointer-events-none",
            )}
          >
            <div className="flex min-w-0 items-center gap-2">
              <CalendarIcon className="size-3.5 shrink-0 text-muted-foreground" />
              <span className="truncate">
                {selectedDate
                  ? format(selectedDate, "dd/MM/yyyy")
                  : placeholder}
              </span>
            </div>
            {!selectedDate && (
              <CalendarIcon className="size-3.5 shrink-0 text-muted-foreground/30" />
            )}
          </button>
        </PopoverTrigger>

        <PopoverContent
          className="w-auto p-0 border-border/80 shadow-md"
          align="start"
          sideOffset={6}
        >
          <Calendar
            selected={selectedDate}
            onSelect={handleSelect}
            showFooter={true}
          />
        </PopoverContent>
      </Popover>

      {selectedDate && !disabled && (
        <button
          type="button"
          onClick={handleClear}
          title="Xóa ngày đã chọn"
          className="absolute right-2.5 z-20 flex size-5 items-center justify-center rounded-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none"
        >
          <X className="size-3" />
        </button>
      )}
    </div>
  );
}
