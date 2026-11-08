// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { ChatMessageItem } from "@/features/conversations/chat-message-item";

afterEach(cleanup);

test("an unavailable old answer shows the server reason instead of a generic notice", () => {
  render(
    <ChatMessageItem
      onOpenCitation={vi.fn()}
      turn={{
        id: "turn-old",
        conversation_id: "chat",
        turn_no: 3,
        question: "Học phí ngành CNTT?",
        resolved_question: null,
        history_turn_ids: [],
        status: "completed",
        error_code: null,
        result: null,
        rewrite_trace: null,
        source_status: "unavailable",
        source_status_reason: "Nguồn của câu trả lời đã bị lưu trữ hoặc xóa.",
        created_at: "2026-11-03T10:00:00Z",
        finished_at: "2026-11-03T10:00:02Z",
      }}
    />,
  );
  expect(
    screen.getByText(/Nguồn của câu trả lời đã bị lưu trữ hoặc xóa/),
  ).toBeTruthy();
  expect(screen.getByText(/Câu trả lời cũ không còn hiệu lực/)).toBeTruthy();
});
