// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { DocumentSpellingProgress } from "@/features/knowledge/document-spelling-report";

afterEach(cleanup);
test("progress shows every active page and stop explicitly drains active groups", () => {
  const stop = vi.fn();
  render(
    <DocumentSpellingProgress
      stopping={false}
      onStop={stop}
      report={{
        version: 0,
        sha256: "hash",
        finished: false,
        batches: [1, 2, 3].map((page) => ({
          page,
          key: `b-${page}`,
          evidenceIds: [`e-${page}`],
          status: page < 3 ? "running" : "pending",
        })),
      }}
    />,
  );
  expect(screen.getByText(/Đang kiểm tra 2 nhóm · Trang 1, 2/)).toBeTruthy();
  fireEvent.click(
    screen.getByRole("button", { name: "Dừng sau các nhóm hiện tại" }),
  );
  expect(stop).toHaveBeenCalledOnce();
});
