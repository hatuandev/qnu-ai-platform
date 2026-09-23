import { vi } from "date-fns/locale";
import { ChevronLeft, ChevronRight } from "lucide-react";
import type * as React from "react";
import {
  DayPicker,
  type DropdownOption,
  type DropdownProps,
  type Matcher,
  type MonthCaptionProps,
  useDayPicker,
} from "react-day-picker";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

function emitDropdownChange(
  onChange: DropdownProps["onChange"],
  value: string,
) {
  if (!onChange) return;
  const target = { value } as HTMLSelectElement;
  onChange({
    target,
    currentTarget: target,
  } as React.ChangeEvent<HTMLSelectElement>);
}

function CalendarDropdown({
  options = [],
  value,
  onChange,
  disabled,
  className,
  variant,
}: DropdownProps & { variant: "month" | "year" }) {
  return (
    <Select
      value={value === undefined ? undefined : String(value)}
      onValueChange={(nextValue) => emitDropdownChange(onChange, nextValue)}
      disabled={disabled}
    >
      <SelectTrigger
        aria-label={variant === "month" ? "Chọn tháng" : "Chọn năm"}
        className={cn(
          "h-8 shrink-0 px-2 text-sm",
          variant === "month" ? "w-36" : "w-24",
          className,
        )}
      >
        <SelectValue />
      </SelectTrigger>
      <SelectContent className="z-[60]">
        {options.map((option: DropdownOption) => (
          <SelectItem
            key={String(option.value)}
            value={String(option.value)}
            disabled={option.disabled}
          >
            {variant === "month"
              ? `Tháng ${String(option.value + 1).padStart(2, "0")}`
              : option.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

function CalendarMonthDropdown(props: DropdownProps) {
  return <CalendarDropdown {...props} variant="month" />;
}

function CalendarYearDropdown(props: DropdownProps) {
  return <CalendarDropdown {...props} variant="year" />;
}

function CalendarCaption({ children, displayIndex }: MonthCaptionProps) {
  const { months, previousMonth, nextMonth, goToMonth } = useDayPicker();
  const isFirst = displayIndex === 0;
  const isLast = displayIndex === months.length - 1;

  return (
    <div className="flex h-9 items-center justify-between gap-2">
      {isFirst ? (
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          aria-label="Tháng trước"
          disabled={!previousMonth}
          onClick={() => previousMonth && goToMonth(previousMonth)}
        >
          <ChevronLeft />
        </Button>
      ) : (
        <span className="size-8 shrink-0" aria-hidden="true" />
      )}
      <div className="flex min-w-0 flex-1 items-center justify-center gap-1">
        {children}
      </div>
      {isLast ? (
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          aria-label="Tháng sau"
          disabled={!nextMonth}
          onClick={() => nextMonth && goToMonth(nextMonth)}
        >
          <ChevronRight />
        </Button>
      ) : (
        <span className="size-8 shrink-0" aria-hidden="true" />
      )}
    </div>
  );
}

function Calendar({
  className,
  classNames,
  disabled,
  minDate,
  maxDate,
  captionLayout = "label",
  ...props
}: React.ComponentProps<typeof DayPicker> & {
  minDate?: Date;
  maxDate?: Date;
}) {
  const disabledMatchers: Matcher[] = [
    ...(disabled ? (Array.isArray(disabled) ? disabled : [disabled]) : []),
    ...(minDate ? [{ before: minDate }] : []),
    ...(maxDate ? [{ after: maxDate }] : []),
  ];

  return (
    <DayPicker
      locale={vi}
      weekStartsOn={1}
      showOutsideDays
      captionLayout={captionLayout}
      hideNavigation
      startMonth={new Date(new Date().getFullYear() - 100, 0, 1)}
      endMonth={new Date(new Date().getFullYear() + 20, 11, 31)}
      disabled={disabledMatchers.length > 0 ? disabledMatchers : undefined}
      className={cn("p-3", className)}
      classNames={{
        months: "flex flex-col gap-4 sm:flex-row",
        month: "space-y-4",
        month_caption: "px-1",
        caption_label: "text-sm font-semibold",
        dropdowns: "flex items-center justify-center gap-1",
        months_dropdown: "w-36",
        years_dropdown: "w-24",
        nav: "hidden",
        button_previous: "hidden",
        button_next: "hidden",
        chevron: "size-4",
        month_grid: "w-full border-collapse",
        weekdays: "flex",
        weekday:
          "w-9 rounded-md text-center text-[12px] font-medium text-muted-foreground",
        week: "flex w-full mt-1",
        day: "relative size-9 p-0 text-center text-[14px]",
        day_button:
          "inline-flex size-9 items-center justify-center rounded-md p-0 font-normal outline-none transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:ring-2 focus-visible:ring-ring/30",
        today: "font-semibold text-primary",
        outside: "text-muted-foreground/50",
        disabled: "pointer-events-none text-muted-foreground/35",
        selected:
          "bg-primary text-primary-foreground hover:bg-primary hover:text-primary-foreground",
        range_start: "rounded-r-none",
        range_middle: "rounded-none bg-accent text-accent-foreground",
        range_end: "rounded-l-none",
        ...classNames,
      }}
      components={{
        MonthCaption: CalendarCaption,
        MonthsDropdown: CalendarMonthDropdown,
        YearsDropdown: CalendarYearDropdown,
        Chevron: ({ orientation }) =>
          orientation === "left" ? (
            <ChevronLeft className="size-4" />
          ) : (
            <ChevronRight className="size-4" />
          ),
      }}
      {...props}
    />
  );
}

export { Calendar };
