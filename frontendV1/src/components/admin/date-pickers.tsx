import {
  endOfMonth,
  format,
  startOfMonth,
  startOfYear,
  subDays,
  subMonths,
} from "date-fns";
import { CalendarDays, Check, Clock3, X } from "lucide-react";
import type * as React from "react";
import { useEffect, useMemo, useState } from "react";
import type { DateRange, Matcher } from "react-day-picker";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Input } from "@/components/ui/input";
import {
  Popover,
  PopoverAnchor,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useIsMobile } from "@/hooks/use-mobile";
import {
  formatDate,
  formatDateRange,
  formatMonthYear,
  getDateInputError,
  parseDateInput,
} from "@/lib/date-utils";
import { cn } from "@/lib/utils";

type DateInputProps = Omit<
  React.ComponentProps<typeof Input>,
  "value" | "defaultValue" | "onChange" | "onBlur"
> & {
  value?: Date;
  onChange?: (value: Date | undefined) => void;
  onBlur?: React.FocusEventHandler<HTMLInputElement>;
  minDate?: Date;
  maxDate?: Date;
  onValidationChange?: (message?: string) => void;
  onCalendarClick?: () => void;
};

function isWithinDateBounds(
  value: Date,
  minDate?: Date,
  maxDate?: Date,
): boolean {
  if (minDate && value < minDate) return false;
  if (maxDate && value > maxDate) return false;
  return true;
}

function DateInput({
  value,
  onChange,
  onBlur,
  minDate,
  maxDate,
  onValidationChange,
  onCalendarClick,
  className,
  ...props
}: DateInputProps) {
  const [inputValue, setInputValue] = useState(formatDate(value));

  useEffect(() => {
    setInputValue(formatDate(value));
  }, [value]);

  const validate = (nextValue: string) => {
    if (nextValue.trim() === "") {
      onValidationChange?.(undefined);
      onChange?.(undefined);
      return;
    }

    const err = getDateInputError(nextValue, minDate, maxDate);
    if (err) {
      onValidationChange?.(err);
      onChange?.(undefined);
      return;
    }

    const parsed = parseDateInput(nextValue);
    onValidationChange?.(undefined);
    onChange?.(parsed);
    setInputValue(formatDate(parsed));
  };

  return (
    <div className="relative">
      <Input
        {...props}
        value={inputValue}
        placeholder="dd/mm/yyyy"
        className={cn(onCalendarClick && "pr-10", className)}
        onChange={(event) => {
          setInputValue(event.target.value);
          if (event.target.value.trim() === "") onChange?.(undefined);
        }}
        onBlur={(event) => {
          validate(event.target.value);
          onBlur?.(event);
        }}
      />
      {onCalendarClick ? (
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          className="absolute top-1/2 right-1 -translate-y-1/2"
          aria-label="Mở lịch"
          onMouseDown={(event) => event.preventDefault()}
          onClick={onCalendarClick}
          disabled={props.disabled}
        >
          <CalendarDays />
        </Button>
      ) : null}
    </div>
  );
}

type DatePickerProps = Omit<
  DateInputProps,
  "onCalendarClick" | "onValidationChange"
> & {
  value?: Date;
  onChange?: (value: Date | undefined) => void;
  onValidationChange?: (message?: string) => void;
  disabledDates?: Matcher | Matcher[];
};

function DatePicker({
  value,
  onChange,
  onValidationChange,
  disabledDates,
  minDate,
  maxDate,
  disabled,
  ...props
}: DatePickerProps) {
  const [open, setOpen] = useState(false);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverAnchor asChild>
        <div>
          <DateInput
            {...props}
            value={value}
            onChange={onChange}
            minDate={minDate}
            maxDate={maxDate}
            disabled={disabled}
            onValidationChange={onValidationChange}
            onCalendarClick={() => setOpen(true)}
          />
        </div>
      </PopoverAnchor>
      <PopoverContent
        align="start"
        className="w-auto max-w-[calc(100vw-1rem)] overflow-auto p-0"
      >
        <Calendar
          mode="single"
          captionLayout="dropdown"
          selected={value}
          onSelect={(nextValue) => {
            if (nextValue) {
              onChange?.(nextValue);
              onValidationChange?.();
              setOpen(false);
            }
          }}
          minDate={minDate}
          maxDate={maxDate}
          disabled={disabledDates}
          defaultMonth={value ?? new Date()}
        />
        <div className="flex justify-end gap-1 border-t p-2">
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => {
              onChange?.(undefined);
              onValidationChange?.();
              setOpen(false);
            }}
          >
            <X />
            Xóa
          </Button>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => {
              const today = new Date();
              if (isWithinDateBounds(today, minDate, maxDate)) {
                onChange?.(today);
                onValidationChange?.();
                setOpen(false);
              }
            }}
          >
            <Check />
            Hôm nay
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}

type DateRangePickerProps = {
  value?: DateRange;
  onChange?: (value: DateRange | undefined) => void;
  minDate?: Date;
  maxDate?: Date;
  disabled?: boolean;
  disabledDates?: Matcher | Matcher[];
  placeholder?: string;
  className?: string;
};

const rangePresets = [
  { label: "Hôm nay", getValue: () => ({ from: new Date(), to: new Date() }) },
  {
    label: "7 ngày qua",
    getValue: () => ({ from: subDays(new Date(), 6), to: new Date() }),
  },
  {
    label: "30 ngày qua",
    getValue: () => ({ from: subDays(new Date(), 29), to: new Date() }),
  },
  {
    label: "90 ngày qua",
    getValue: () => ({ from: subDays(new Date(), 89), to: new Date() }),
  },
  {
    label: "Tháng này",
    getValue: () => ({ from: startOfMonth(new Date()), to: new Date() }),
  },
  {
    label: "Tháng trước",
    getValue: () => {
      const previous = subMonths(new Date(), 1);
      return { from: startOfMonth(previous), to: endOfMonth(previous) };
    },
  },
  {
    label: "Năm nay",
    getValue: () => ({ from: startOfYear(new Date()), to: new Date() }),
  },
];

function DateRangePicker({
  value,
  onChange,
  minDate,
  maxDate,
  disabled,
  disabledDates,
  placeholder = "Chọn khoảng thời gian",
  className,
}: DateRangePickerProps) {
  const [open, setOpen] = useState(false);
  const isMobile = useIsMobile();

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          disabled={disabled}
          className={cn("w-full justify-start font-normal", className)}
        >
          <CalendarDays />
          <span className={cn(!value?.from && "text-muted-foreground")}>
            {formatDateRange(value) || placeholder}
          </span>
        </Button>
      </PopoverTrigger>
      <PopoverContent
        align="start"
        className="w-auto max-w-[calc(100vw-1rem)] overflow-auto p-0"
      >
        <Calendar
          mode="range"
          captionLayout="label"
          selected={value}
          onSelect={(nextValue) => {
            onChange?.(nextValue);
            if (nextValue?.from && nextValue.to) setOpen(false);
          }}
          numberOfMonths={isMobile ? 1 : 2}
          minDate={minDate}
          maxDate={maxDate}
          disabled={disabledDates}
          defaultMonth={value?.from ?? new Date()}
        />
        <div className="flex flex-wrap items-center justify-between gap-1 border-t p-2">
          <div className="flex flex-wrap gap-1">
            {rangePresets.map((preset) => (
              <Button
                key={preset.label}
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => {
                  onChange?.(preset.getValue());
                  setOpen(false);
                }}
              >
                {preset.label}
              </Button>
            ))}
          </div>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => {
              onChange?.(undefined);
              setOpen(false);
            }}
          >
            <X />
            Xóa
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}

type MonthYearPickerProps = {
  value?: Date;
  onChange?: (value: Date | undefined) => void;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
};

function MonthYearPicker({
  value,
  onChange,
  disabled,
  placeholder = "Chọn tháng",
  className,
}: MonthYearPickerProps) {
  const [open, setOpen] = useState(false);
  const currentYear = new Date().getFullYear();
  const years = useMemo(
    () => Array.from({ length: 121 }, (_, index) => currentYear - 100 + index),
    [currentYear],
  );
  const months = Array.from({ length: 12 }, (_, index) => index);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          disabled={disabled}
          className={cn("w-full justify-start font-normal", className)}
        >
          <CalendarDays />
          <span className={cn(!value && "text-muted-foreground")}>
            {formatMonthYear(value) || placeholder}
          </span>
        </Button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-64 space-y-3">
        <div className="text-sm font-semibold">Chọn tháng và năm</div>
        <div className="grid grid-cols-2 gap-2">
          <Select
            value={value ? String(value.getMonth()) : undefined}
            onValueChange={(month) =>
              onChange?.(
                new Date(value?.getFullYear() ?? currentYear, Number(month), 1),
              )
            }
          >
            <SelectTrigger aria-label="Tháng">
              <SelectValue placeholder="Tháng" />
            </SelectTrigger>
            <SelectContent>
              {months.map((month) => (
                <SelectItem key={month} value={String(month)}>
                  Tháng {String(month + 1).padStart(2, "0")}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select
            value={value ? String(value.getFullYear()) : undefined}
            onValueChange={(year) =>
              onChange?.(
                new Date(
                  Number(year),
                  value?.getMonth() ?? new Date().getMonth(),
                  1,
                ),
              )
            }
          >
            <SelectTrigger aria-label="Năm">
              <SelectValue placeholder="Năm" />
            </SelectTrigger>
            <SelectContent>
              {years.map((year) => (
                <SelectItem key={year} value={String(year)}>
                  {year}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex justify-end gap-1 border-t pt-2">
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => onChange?.(undefined)}
          >
            <X />
            Xóa
          </Button>
          <Button type="button" size="sm" onClick={() => setOpen(false)}>
            Xong
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}

type DateTimePickerProps = Omit<DatePickerProps, "value" | "onChange"> & {
  value?: Date;
  onChange?: (value: Date | undefined) => void;
};

type TimeInputProps = Omit<
  React.ComponentProps<typeof Input>,
  "value" | "defaultValue" | "onChange"
> & {
  value?: string;
  onChange?: (value: string | undefined) => void;
  onValidationChange?: (message?: string) => void;
};

function TimeInput({
  value,
  onChange,
  onValidationChange,
  className,
  ...props
}: TimeInputProps) {
  const [inputValue, setInputValue] = useState(value ?? "");

  useEffect(() => setInputValue(value ?? ""), [value]);

  const validate = (nextValue: string) => {
    if (nextValue.trim() === "") {
      onValidationChange?.();
      onChange?.(undefined);
      return;
    }
    if (!/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(nextValue)) {
      onValidationChange?.("Thời gian không hợp lệ. Dùng định dạng HH:mm.");
      return;
    }
    onValidationChange?.();
    onChange?.(nextValue);
  };

  return (
    <div className="relative">
      <Input
        {...props}
        value={inputValue}
        placeholder="HH:mm"
        inputMode="numeric"
        maxLength={5}
        className={cn("pr-10", className)}
        onChange={(event) => setInputValue(event.target.value)}
        onBlur={(event) => validate(event.target.value)}
      />
      <Clock3 className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-muted-foreground" />
    </div>
  );
}

function DateTimePicker({
  value,
  onChange,
  className,
  ...props
}: DateTimePickerProps) {
  const timeValue = value ? format(value, "HH:mm") : undefined;

  return (
    <div
      className={cn("grid gap-2 sm:grid-cols-[minmax(0,1fr)_120px]", className)}
    >
      <DatePicker value={value} onChange={onChange} {...props} />
      <TimeInput
        aria-label="Thời gian"
        value={timeValue}
        onChange={(nextTime) => {
          if (!nextTime) {
            onChange?.(undefined);
            return;
          }
          const [hours, minutes] = nextTime.split(":").map(Number);
          const next = value ? new Date(value) : new Date();
          next.setHours(hours, minutes, 0, 0);
          onChange?.(next);
        }}
        disabled={props.disabled}
      />
    </div>
  );
}

export {
  DateInput,
  DatePicker,
  DateRangePicker,
  DateTimePicker,
  MonthYearPicker,
  TimeInput,
};
