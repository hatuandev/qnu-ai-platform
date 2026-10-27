// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { ChatView } from "@/features/conversations/chat-view";
import {
  draftToFilter,
  EMPTY_METADATA_FILTER_DRAFT,
  isMetadataFilterDraftEmpty,
} from "@/features/rag/metadata-filter-fields";

const ports = vi.hoisted(() => ({ send: vi.fn() }));
vi.mock("@/app/auth/v1", () => ({ useV1Auth: () => ({ sessionId: 1 }) }));
vi.mock("@tanstack/react-router", () => ({
  Link: ({ children }: { children: ReactNode }) => <span>{children}</span>,
}));
vi.mock("@/features/assistants/queries", () => ({
  useAssistantQuery: () => ({
    data: { id: "a", name: "Synthetic bot", is_active: true },
  }),
}));
vi.mock("@/features/conversations/conversation-rename-dialog", () => ({
  ConversationRenameDialog: () => null,
}));
vi.mock("@/features/conversations/chat-message-item", () => ({
  ChatMessageItem: () => null,
}));
vi.mock("@/features/conversations/requests", () => ({
  getConversation: async () => ({
    id: "chat",
    assistant_id: "a",
    title: "Synthetic chat",
    status: "active",
    last_turn_no: 0,
  }),
  listTurns: async () => [],
  sendTurn: ports.send,
}));
const clients: QueryClient[] = [];
beforeEach(() => {
  ports.send.mockReset();
  ports.send.mockResolvedValue({
    id: "turn-one",
    turn_no: 1,
    status: "completed",
  });
});
afterEach(() => {
  cleanup();
  for (const client of clients.splice(0)) client.clear();
});

test.each(["Năm dữ liệu", "Năm ban hành"])(
  "invalid %s blocks click and Enter without losing the question, then permits correction",
  async (label) => {
    const client = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    clients.push(client);
    render(
      <QueryClientProvider client={client}>
        <ChatView workspaceId="w" conversationId="chat" />
      </QueryClientProvider>,
    );
    const question = await screen.findByPlaceholderText(/Nhập câu hỏi/);
    fireEvent.click(screen.getByRole("button", { name: /Phạm vi metadata/ }));
    fireEvent.change(screen.getByLabelText(label), {
      target: { value: "202" },
    });
    fireEvent.change(question, { target: { value: "Synthetic question" } });
    const submit = screen.getByRole("button", { name: "Gửi câu hỏi" });
    expect(submit.hasAttribute("disabled")).toBe(true);
    fireEvent.click(submit);
    fireEvent.keyDown(question, { key: "Enter" });
    await act(async () => {
      await Promise.resolve();
    });
    expect(ports.send).not.toHaveBeenCalled();
    expect((question as HTMLTextAreaElement).value).toBe("Synthetic question");
    expect(screen.getByLabelText(label).getAttribute("aria-invalid")).toBe(
      "true",
    );
    fireEvent.change(screen.getByLabelText(label), {
      target: { value: "2026" },
    });
    fireEvent.keyDown(question, { key: "Enter" });
    await waitFor(() => expect(ports.send).toHaveBeenCalledTimes(1));
    expect(ports.send.mock.calls[0][3]).toEqual(
      expect.objectContaining({
        metadata_filter: {
          [label === "Năm dữ liệu" ? "data_year" : "issued_year"]: 2026,
        },
      }),
    );
  },
);

test("invalid nonempty scope never converts to an unset filter", () => {
  const invalid = { ...EMPTY_METADATA_FILTER_DRAFT, data_year: "202" };
  expect(isMetadataFilterDraftEmpty(invalid)).toBe(false);
  expect(() => draftToFilter(invalid)).toThrow(/không hợp lệ/);
  expect(draftToFilter(EMPTY_METADATA_FILTER_DRAFT)).toEqual({});
});
