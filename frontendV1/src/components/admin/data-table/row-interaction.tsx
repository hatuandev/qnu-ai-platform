import type { KeyboardEvent, MouseEvent, ReactNode } from "react";

/**
 * Marks a cell that owns its own controls (checkbox, menu, links). The row click
 * handler ignores events coming from inside it, so selecting a row or opening a
 * menu never navigates. This replaces the old `<div onClick={stopPropagation}>`
 * wrappers: a plain element must not carry a click handler just to stop
 * propagation, because it is not reachable by keyboard and confuses assistive
 * technology.
 */
export const ROW_CONTROL_ATTR = "data-row-control";

export function isRowControlEvent(event: MouseEvent<HTMLElement>): boolean {
  const target = event.target;
  return (
    target instanceof Element &&
    target.closest(`[${ROW_CONTROL_ATTR}]`) !== null
  );
}

export function RowControl({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <div data-row-control="" className={className}>
      {children}
    </div>
  );
}

/**
 * Keyboard path for a clickable table row.
 *
 * The row keeps its native table semantics (no `role="button"` on a `<tr>`);
 * only tab focus and Enter/Space activation are added. Keys pressed inside a
 * focused cell control are left alone, so a checkbox or menu button keeps its
 * own behaviour.
 */
export function rowActivationProps(onActivate: () => void) {
  return {
    tabIndex: 0,
    onKeyDown: (event: KeyboardEvent<HTMLElement>) => {
      if (event.target !== event.currentTarget) return;
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      onActivate();
    },
  };
}

/** Focus styling shared by every clickable row. */
export const rowActivationClassName =
  "focus-visible:bg-muted/60 focus-visible:outline-none";
