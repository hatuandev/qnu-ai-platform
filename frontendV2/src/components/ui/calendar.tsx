import {
  addMonths,
  addYears,
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  isToday as isDayToday,
  isSameDay,
  isSameMonth,
  startOfMonth,
  startOfWeek,
  subMonths,
  subYears,
} from "date-fns";
import { vi } from "date-fns/locale/vi";
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react";
import * as React from "react";
import { cn } from "@/lib/utils";

export interface CalendarProps {
  selected?: Date | null;
  onSelect?: (date: Date | null) => void;
  className?: string;
  disabled?: (date: Date) => boolean;
  showFooter?: boolean;
}

export function Calendar({
  selected,
  onSelect,
  className,
  disabled,
  showFooter = true,
}: CalendarProps) {
  const [currentMonth, setCurrentMonth] = React.useState<Date>(
    () => selected || new Date(),
  );

  React.useEffect(() => {
    if (selected) {
      setCurrentMonth(selected);
    }
  }, [selected]);

  const monthStart = startOfMonth(currentMonth);
  const monthEnd = endOfMonth(monthStart);
  // Week starts on Monday (1)
  const startDate = startOfWeek(monthStart, { weekStartsOn: 1 });
  const endDate = endOfWeek(monthEnd, { weekStartsOn: 1 });

  const days = eachDayOfInterval({ start: startDate, end: endDate });
  const weekDays = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];

  const handlePrevYear = () => setCurrentMonth(subYears(currentMonth, 1));
  const handleNextYear = () => setCurrentMonth(addYears(currentMonth, 1));
  const handlePrevMonth = () => setCurrentMonth(subMonths(currentMonth, 1));
  const handleNextMonth = () => setCurrentMonth(addMonths(currentMonth, 1));

  const handleToday = () => {
    const today = new Date();
    setCurrentMonth(today);
    onSelect?.(today);
  };

  const handleClear = () => {
    onSelect?.(null);
  };

  return (
    <div className={cn("w-[268px] select-none p-3", className)}>
      {/* Header with Month/Year Navigation */}
      <div className="mb-2 flex items-center justify-between border-b border-border/50 pb-2">
        <div className="flex items-center gap-0.5">
          <button
            type="button"
            onClick={handlePrevYear}
            className="flex size-6 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none"
            title="Năm trước"
          >
            <ChevronsLeft className="size-3.5" />
          </button>
          <button
            type="button"
            onClick={handlePrevMonth}
            className="flex size-6 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none"
            title="Tháng trước"
          >
            <ChevronLeft className="size-3.5" />
          </button>
        </div>

        <span className="px-1 text-xs font-semibold capitalize text-foreground">
          {format(currentMonth, "MMMM 'năm' yyyy", { locale: vi })}
        </span>

        <div className="flex items-center gap-0.5">
          <button
            type="button"
            onClick={handleNextMonth}
            className="flex size-6 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none"
            title="Tháng sau"
          >
            <ChevronRight className="size-3.5" />
          </button>
          <button
            type="button"
            onClick={handleNextYear}
            className="flex size-6 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none"
            title="Năm sau"
          >
            <ChevronsRight className="size-3.5" />
          </button>
        </div>
      </div>

      {/* Weekday headers */}
      <div className="mb-1 grid grid-cols-7 gap-1 text-center">
        {weekDays.map((wd) => (
          <div
            key={wd}
            className="flex size-8 items-center justify-center text-[11px] font-medium text-muted-foreground"
          >
            {wd}
          </div>
        ))}
      </div>

      {/* Days grid */}
      <div className="grid grid-cols-7 gap-1">
        {days.map((day) => {
          const isSelected = selected ? isSameDay(day, selected) : false;
          const isCurrentMonth = isSameMonth(day, monthStart);
          const isToday = isDayToday(day);
          const isDayDisabled = disabled ? disabled(day) : false;

          return (
            <button
              key={day.toISOString()}
              type="button"
              disabled={isDayDisabled}
              onClick={() => onSelect?.(day)}
              className={cn(
                "flex size-8 items-center justify-center rounded-md text-xs transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
                !isCurrentMonth && "text-muted-foreground/30",
                isCurrentMonth &&
                  !isSelected &&
                  "text-foreground hover:bg-accent hover:text-accent-foreground",
                isToday &&
                  !isSelected &&
                  "border border-primary/50 font-semibold text-primary",
                isSelected &&
                  "bg-primary font-semibold text-primary-foreground shadow-xs hover:bg-primary/95",
                isDayDisabled &&
                  "pointer-events-none cursor-not-allowed opacity-30",
              )}
            >
              {format(day, "d")}
            </button>
          );
        })}
      </div>

      {/* Footer quick actions */}
      {showFooter && (
        <div className="mt-2.5 flex items-center justify-between border-t border-border/50 pt-2 text-xs">
          <button
            type="button"
            onClick={handleClear}
            className="rounded px-1.5 py-0.5 text-[11px] font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-destructive"
          >
            Xóa chọn
          </button>
          <button
            type="button"
            onClick={handleToday}
            className="rounded px-1.5 py-0.5 text-[11px] font-medium text-primary transition-colors hover:bg-primary/10 hover:text-primary/90"
          >
            Hôm nay
          </button>
        </div>
      )}
    </div>
  );
}
