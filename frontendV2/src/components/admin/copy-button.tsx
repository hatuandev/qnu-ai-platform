import { Check, Copy } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

export interface CopyButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  value: string;
  label?: string;
  tooltip?: string;
  copiedTooltip?: string;
  showToast?: boolean;
}

export function CopyButton({
  value,
  label,
  tooltip = "Sao chép",
  copiedTooltip = "Đã sao chép!",
  showToast = false,
  className,
  ...props
}: CopyButtonProps) {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = React.useCallback(
    async (e: React.MouseEvent<HTMLButtonElement>) => {
      e.stopPropagation();
      e.preventDefault();
      if (!value) return;

      try {
        if (navigator?.clipboard?.writeText) {
          await navigator.clipboard.writeText(value);
        } else {
          // Fallback for older browsers / non-secure contexts
          const textarea = document.createElement("textarea");
          textarea.value = value;
          textarea.style.position = "fixed";
          textarea.style.opacity = "0";
          document.body.appendChild(textarea);
          textarea.focus();
          textarea.select();
          document.execCommand("copy");
          document.body.removeChild(textarea);
        }

        setCopied(true);
        if (showToast) {
          toast.success(
            label ? `Đã sao chép ${label}` : "Đã sao chép vào bộ nhớ tạm",
          );
        }
        setTimeout(() => setCopied(false), 2000);
      } catch {
        toast.error("Không thể sao chép vào bộ nhớ tạm");
      }
    },
    [value, label, showToast],
  );

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className={cn(
            "size-6 shrink-0 rounded-md text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:ring-1",
            copied &&
              "text-emerald-600 hover:text-emerald-600 dark:text-emerald-400",
            className,
          )}
          onClick={handleCopy}
          aria-label={label ? `Sao chép ${label}` : tooltip}
          {...props}
        >
          {copied ? (
            <Check className="size-3.5 animate-in zoom-in-50 duration-200" />
          ) : (
            <Copy className="size-3.5" />
          )}
        </Button>
      </TooltipTrigger>
      <TooltipContent side="top" className="text-xs">
        {copied ? copiedTooltip : tooltip}
      </TooltipContent>
    </Tooltip>
  );
}

export interface CopyableTextProps {
  value: string;
  displayValue?: React.ReactNode;
  label?: string;
  className?: string;
  textClassName?: string;
  isMono?: boolean;
}

export function CopyableText({
  value,
  displayValue,
  label,
  className,
  textClassName,
  isMono = true,
}: CopyableTextProps) {
  if (!value) return null;

  return (
    <span
      className={cn("inline-flex items-center gap-1 group/copyable", className)}
    >
      <span
        className={cn(
          "truncate",
          isMono && "font-mono text-xs font-medium tracking-tight",
          textClassName,
        )}
      >
        {displayValue ?? value}
      </span>
      <CopyButton
        value={value}
        label={label}
        className="opacity-0 group-hover/copyable:opacity-100 focus:opacity-100 transition-opacity"
      />
    </span>
  );
}
