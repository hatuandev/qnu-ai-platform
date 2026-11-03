// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { ChatMessageItem } from "@/features/conversations/chat-message-item";

afterEach(cleanup);

test("renders a greeting as chat text without an evidence warning", () => {
  render(
    <ChatMessageItem
      onOpenCitation={vi.fn()}
      turn={{
        id: "turn-1",
        conversation_id: "chat",
        turn_no: 1,
        question: "Xin chào",
        resolved_question: null,
        history_turn_ids: [],
        status: "completed",
        error_code: null,
        result: {
          id: "turn-1",
          status: "direct_reply",
          route: "greeting",
          answer: "Chào bạn! Mình là Trợ lý tuyển sinh.",
        },
        rewrite_trace: null,
        source_status: "current",
        created_at: "2026-11-03T10:00:00Z",
        finished_at: "2026-11-03T10:00:00Z",
      }}
    />,
  );
  expect(screen.getByText("Chào bạn! Mình là Trợ lý tuyển sinh.")).toBeTruthy();
  expect(screen.queryByText(/Không đủ bằng chứng/)).toBeNull();
});
