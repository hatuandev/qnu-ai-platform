// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, expect, test, vi } from "vitest";
import { ChatView } from "../src/features/conversations/chat-view";

const ports = vi.hoisted(() => ({ list: vi.fn(), send: vi.fn(), count: 60 }));
vi.mock("@/app/auth/v1", () => ({ useV1Auth: () => ({ sessionId: 1 }) }));
vi.mock("@tanstack/react-router", () => ({
  Link: ({ children }: { children: ReactNode }) => <span>{children}</span>,
}));
vi.mock("@/features/assistants/queries", () => ({
  useAssistantQuery: () => ({
    data: { id: "a", name: "Bot", is_active: true },
  }),
}));
vi.mock("@/features/conversations/conversation-rename-dialog", () => ({
  ConversationRenameDialog: () => null,
}));
vi.mock("@/features/conversations/chat-message-item", () => ({
  ChatMessageItem: ({
    turn,
    isSubmitting,
  }: {
    turn: { turn_no: number; question?: string };
    isSubmitting?: boolean;
  }) => (isSubmitting ? <p>{turn.question}</p> : <p>Lượt {turn.turn_no}</p>),
}));
vi.mock("@/features/conversations/requests", () => ({
  getConversation: async () => ({
    id: "chat",
    assistant_id: "a",
    title: "Chat",
    status: "active",
    last_turn_no: ports.count,
  }),
  listTurns: ports.list,
  sendTurn: ports.send,
}));
afterEach(cleanup);
test("F3: show latest turns, load earlier pages and retain a new turn beyond 50", async () => {
  ports.count = 60;
  Element.prototype.scrollTo = vi.fn();
  ports.list.mockImplementation(async (_client, _w, _c, params) =>
    Array.from({ length: ports.count }, (_, i) => ({
      id: `turn-${i + 1}`,
      turn_no: i + 1,
      status: "completed",
    })).slice(params.offset, params.offset + params.limit),
  );
  let finishSend = () => {};
  ports.send.mockImplementation(
    () =>
      new Promise((resolve) => {
        finishSend = () => {
          ports.count += 1;
          resolve({
            id: `turn-${ports.count}`,
            turn_no: ports.count,
            status: "completed",
          });
        };
      }),
  );
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <ChatView workspaceId="w" conversationId="chat" />
    </QueryClientProvider>,
  );
  expect(await screen.findByText("Lượt 60")).toBeTruthy();
  fireEvent.click(
    screen.getByRole("button", { name: /Tải các lượt trước đó/ }),
  );
  expect(await screen.findByText("Lượt 1")).toBeTruthy();
  expect(screen.getByText("Lượt 60")).toBeTruthy();
  fireEvent.change(screen.getByPlaceholderText(/Nhập câu hỏi/), {
    target: { value: "Next question" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Gửi câu hỏi" }));
  expect(await screen.findByText("Next question")).toBeTruthy();
  expect(screen.queryByText("Lượt 61")).toBeNull();
  expect(ports.send).toHaveBeenCalledTimes(1);
  finishSend();
  await waitFor(() => expect(screen.getByText("Lượt 61")).toBeTruthy());
  expect(screen.queryByText("Next question")).toBeNull();
  expect(screen.getAllByText("Lượt 61")).toHaveLength(1);
  expect(screen.getAllByText("Lượt 60")).toHaveLength(1);
  expect(ports.send).toHaveBeenCalledTimes(1);
  client.clear();
});
