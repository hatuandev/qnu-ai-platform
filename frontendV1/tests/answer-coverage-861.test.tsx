// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import {
  type AnswerCoverage,
  AnswerCoverageNotice,
} from "../src/features/rag/answer-coverage";

afterEach(cleanup);
const partial: AnswerCoverage = {
  status: "partial",
  basis: "model_requirements_and_source_citations",
  requirements: [
    { label: "Danh sách giấy tờ cụ thể", status: "missing", evidence_ids: [] },
  ],
  structures: [],
};

test("A partial answer explains the missing requirement without exposing IDs", () => {
  render(<AnswerCoverageNotice coverage={partial} />);
  expect(screen.getByText(/mới bao quát một phần/)).toBeTruthy();
  expect(screen.getByText(/Danh sách giấy tờ cụ thể/)).toBeTruthy();
  expect(screen.queryByText(/model_requirements/)).toBeNull();
});

test("Uncovered structural units stay visible even if the model claimed coverage", () => {
  render(
    <AnswerCoverageNotice
      coverage={{
        ...partial,
        requirements: [],
        structures: [
          {
            label: "Điều 4",
            required_units: 4,
            provided_units: 4,
            cited_units: 2,
            status: "partial",
          },
        ],
      }}
    />,
  );
  expect(
    screen.getByText(/Chưa bao quát hết nội dung của Điều 4/),
  ).toBeTruthy();
});

test("Legacy and complete assessments do not show a misleading verification badge", () => {
  const { container, rerender } = render(<AnswerCoverageNotice />);
  expect(container.textContent).toBe("");
  rerender(
    <AnswerCoverageNotice coverage={{ ...partial, status: "complete" }} />,
  );
  expect(container.textContent).toBe("");
});

test("Missing evidence opens the exact source set rather than an unrelated answer citation", () => {
  const open = vi.fn();
  render(
    <AnswerCoverageNotice
      coverage={{
        ...partial,
        requirements: [
          {
            label: "Qualifications",
            status: "missing",
            evidence_ids: ["E7", "E8"],
          },
        ],
        structures: [
          {
            label: "Article 4",
            status: "partial",
            required_units: 4,
            provided_units: 4,
            cited_units: 2,
            uncovered_evidence_ids: ["E8", "E9"],
          },
        ],
      }}
      onOpenSources={open}
    />,
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Xem nguồn cần đối chiếu" }),
  );
  expect(open).toHaveBeenCalledWith(["E7", "E8", "E9"]);
});
