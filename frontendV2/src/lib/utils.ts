import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Strips internal technical IDs and hex suffixes from user-facing text
 * according to `.agents/rules/ui-standards.md` (e.g. `(col_...)`, `(f332310)`, `(ast_...)`).
 */
export function sanitizeDisplayText(text: string | null | undefined): string {
  if (!text) return "";
  return text
    .replace(/\s*\((?:col|ast|ws|doc|idx|src|rev|prv|usr|act)_[a-zA-Z0-9_-]+\)/gi, "")
    .replace(/\s*\([0-9a-f]{6,}\)/gi, "")
    .replace(/\s*\([a-f0-9]{7,}\)/gi, "")
    .trim();
}
