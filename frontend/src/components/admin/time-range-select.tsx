import { CalendarDays } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export const timeRangeValues = ["7d", "30d", "90d", "1y"] as const;
export type TimeRange = (typeof timeRangeValues)[number];

const timeRangeLabels: Record<TimeRange, string> = {
  "7d": "7 ngày qua",
  "30d": "30 ngày qua",
  "90d": "90 ngày qua",
  "1y": "Năm nay",
};

export function TimeRangeSelect({
  value,
  onChange,
}: {
  value: TimeRange;
  onChange: (value: TimeRange) => void;
}) {
  return (
    <div className="flex items-center gap-2">
      <CalendarDays
        className="hidden size-4 text-muted-foreground sm:block"
        aria-hidden="true"
      />
      <Select
        value={value}
        onValueChange={(next) => onChange(next as TimeRange)}
      >
        <SelectTrigger className="w-[148px]" aria-label="Khoảng thời gian">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {timeRangeValues.map((range) => (
            <SelectItem key={range} value={range}>
              {timeRangeLabels[range]}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

export function timeRangeLabel(range: TimeRange) {
  return timeRangeLabels[range];
}
