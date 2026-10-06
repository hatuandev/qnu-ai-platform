import { format } from "date-fns";

export const DATE_DISPLAY_FORMAT = "dd/MM/yyyy";
export const DATE_TIME_DISPLAY_FORMAT = "dd/MM/yyyy HH:mm";
export const MONTH_YEAR_DISPLAY_FORMAT = "MM/yyyy";

export type DateRangeValue = {
  from?: Date;
  to?: Date;
};

export function formatDate(date: Date | undefined): string {
  return date ? format(date, DATE_DISPLAY_FORMAT) : "";
}

export function formatDateTime(date: Date | undefined): string {
  return date ? format(date, DATE_TIME_DISPLAY_FORMAT) : "";
}

/** Format an ISO string from the API as dd/MM/yyyy (empty when missing). */
export function formatDateValue(value?: string | null): string {
  return value ? format(new Date(value), DATE_DISPLAY_FORMAT) : "";
}

/** Format an ISO string from the API as dd/MM/yyyy HH:mm (empty when missing). */
export function formatDateTimeValue(value?: string | null): string {
  return value ? format(new Date(value), DATE_TIME_DISPLAY_FORMAT) : "";
}

export function formatMonthYear(date: Date | undefined): string {
  return date ? format(date, MONTH_YEAR_DISPLAY_FORMAT) : "";
}

export function formatDateRange(range: DateRangeValue | undefined): string {
  if (!range?.from) return "";
  const from = formatDate(range.from);
  return range.to ? `${from} – ${formatDate(range.to)}` : from;
}

/** Parse Vietnamese display input explicitly as day/month/year in local time. */
export function parseDateInput(value: string): Date | undefined {
  const match = value.trim().match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (!match) return undefined;

  const [, dayText, monthText, yearText] = match;
  const day = Number(dayText);
  const month = Number(monthText);
  const year = Number(yearText);
  const date = new Date(year, month - 1, day);

  if (
    date.getFullYear() !== year ||
    date.getMonth() !== month - 1 ||
    date.getDate() !== day
  ) {
    return undefined;
  }

  return date;
}

/** Validate user date input string and return an error message if invalid, or undefined if valid. */
export function getDateInputError(
  value: string,
  minDate?: Date,
  maxDate?: Date,
): string | undefined {
  const trimmed = value.trim();
  if (trimmed === "") return undefined;

  const match = trimmed.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (!match) {
    return `Định dạng ngày phải là ${DATE_DISPLAY_FORMAT} (ví dụ: 30/09/2026).`;
  }

  const [, dayText, monthText, yearText] = match;
  const day = Number(dayText);
  const month = Number(monthText);
  const year = Number(yearText);

  if (year < 1900 || year > 2100) {
    return "Năm không hợp lệ (1900 - 2100).";
  }

  if (month < 1 || month > 12) {
    return "Tháng không hợp lệ (1 - 12).";
  }

  const maxDaysInMonth = new Date(year, month, 0).getDate();
  if (day < 1 || day > maxDaysInMonth) {
    return `Ngày không hợp lệ (tháng ${month}/${year} chỉ có ${maxDaysInMonth} ngày).`;
  }

  const date = new Date(year, month - 1, day);
  if (minDate) {
    const minDay = new Date(
      minDate.getFullYear(),
      minDate.getMonth(),
      minDate.getDate(),
    ).getTime();
    if (date.getTime() < minDay) {
      return `Ngày không được trước ngày ${formatDate(minDate)}.`;
    }
  }

  if (maxDate) {
    const maxDay = new Date(
      maxDate.getFullYear(),
      maxDate.getMonth(),
      maxDate.getDate(),
    ).getTime();
    if (date.getTime() > maxDay) {
      return `Ngày không được vượt quá ngày ${formatDate(maxDate)}.`;
    }
  }

  return undefined;
}

export function isValidDateInput(value: string): boolean {
  return value.trim() === "" || parseDateInput(value) !== undefined;
}

/** Parse a yyyy-MM-dd storage string into a local Date (date-only fields). */
export function parseDateOnly(value: string | undefined): Date | undefined {
  if (!value) return undefined;
  const [year, month, day] = value.slice(0, 10).split("-").map(Number);
  if (![year, month, day].every(Number.isFinite)) return undefined;
  return new Date(year, month - 1, day);
}

/** Format a Date as yyyy-MM-dd for storage inputs (date-only fields). */
export function formatDateOnly(value: Date | undefined): string {
  return value ? format(value, "yyyy-MM-dd") : "";
}
