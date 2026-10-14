import type { ComponentProps } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

/** Shared presentation only: callers own provider identity and server state. */
export function OptionSelect({
  options,
  placeholder = "Chọn giá trị",
  triggerProps,
  ...props
}: ComponentProps<typeof Select> & {
  options: readonly SelectOption[];
  placeholder?: string;
  triggerProps: ComponentProps<typeof SelectTrigger>;
}) {
  return (
    <Select {...props}>
      <SelectTrigger
        className="w-full min-w-0 h-auto min-h-9 [&>span]:whitespace-normal [&>span]:break-words [&>span]:text-left"
        {...triggerProps}
      >
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent className="max-w-[calc(100vw-2rem)]">
        {options.map((option) => (
          <SelectItem
            key={option.value}
            value={option.value}
            disabled={option.disabled}
            className="whitespace-normal break-words"
          >
            {option.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
