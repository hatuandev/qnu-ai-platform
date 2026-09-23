import { Search, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export interface DebouncedSearchInputProps
  extends Omit<React.ComponentProps<typeof Input>, "value" | "onChange"> {
  value: string;
  onChange: (value: string) => void;
  debounceMs?: number;
  containerClassName?: string;
  showSearchIcon?: boolean;
  showClearButton?: boolean;
}

export function DebouncedSearchInput({
  value: externalValue,
  onChange,
  debounceMs = 300,
  containerClassName,
  className,
  placeholder = "Tìm kiếm...",
  showSearchIcon = true,
  showClearButton = true,
  ...props
}: DebouncedSearchInputProps) {
  const [localValue, setLocalValue] = useState(externalValue ?? "");
  const isComposingRef = useRef(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync external value to local state when external value changes
  // and user is not currently in an active IME composition
  useEffect(() => {
    if (!isComposingRef.current && (externalValue ?? "") !== localValue) {
      setLocalValue(externalValue ?? "");
    }
  }, [externalValue]);

  // Clean up debounce timer on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  const triggerChange = (nextValue: string) => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    timeoutRef.current = setTimeout(() => {
      onChange(nextValue);
    }, debounceMs);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const nextValue = e.target.value;
    setLocalValue(nextValue);

    // If Vietnamese IME is actively composing (e.g. typing double keys 'aa'),
    // do not trigger parent debounce/navigation until composition completes
    if (!isComposingRef.current) {
      triggerChange(nextValue);
    }
  };

  const handleCompositionStart = () => {
    isComposingRef.current = true;
  };

  const handleCompositionEnd = (
    e: React.CompositionEvent<HTMLInputElement>,
  ) => {
    isComposingRef.current = false;
    const nextValue = e.currentTarget.value;
    setLocalValue(nextValue);
    triggerChange(nextValue);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      onChange(localValue);
    }
  };

  const handleClear = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    setLocalValue("");
    onChange("");
  };

  return (
    <div className={cn("relative w-full", containerClassName)}>
      {showSearchIcon ? (
        <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
      ) : null}
      <Input
        value={localValue}
        onChange={handleInputChange}
        onCompositionStart={handleCompositionStart}
        onCompositionEnd={handleCompositionEnd}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        className={cn(
          showSearchIcon && "pl-9",
          showClearButton && localValue && "pr-8",
          className,
        )}
        {...props}
      />
      {showClearButton && localValue ? (
        <button
          type="button"
          onClick={handleClear}
          className="absolute top-1/2 right-2.5 -translate-y-1/2 text-muted-foreground hover:text-foreground focus:outline-none"
          aria-label="Xóa tìm kiếm"
        >
          <X className="size-3.5" />
        </button>
      ) : null}
    </div>
  );
}
