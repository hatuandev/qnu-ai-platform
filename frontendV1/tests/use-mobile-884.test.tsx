// @vitest-environment jsdom
import { act, cleanup, render } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { useIsMobile } from "@/hooks/use-mobile";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

test("mobile dialogs use the correct layout on the first render and still follow resize", () => {
  const change = new Set<() => void>();
  const media = {
    matches: true,
    addEventListener: (_: string, fn: () => void) => change.add(fn),
    removeEventListener: (_: string, fn: () => void) => change.delete(fn),
  };
  vi.stubGlobal("matchMedia", () => media);
  const renders: boolean[] = [];
  function Probe() {
    const isMobile = useIsMobile();
    renders.push(isMobile);
    return <span>{isMobile ? "mobile" : "desktop"}</span>;
  }
  const view = render(<Probe />);
  expect(renders[0]).toBe(true);
  act(() => {
    media.matches = false;
    for (const listener of change) listener();
  });
  expect(renders.at(-1)).toBe(false);
  view.unmount();
  expect(change.size).toBe(0);
});
