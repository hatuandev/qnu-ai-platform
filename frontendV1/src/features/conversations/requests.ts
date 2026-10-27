import type { V1Client } from "@/app/api/v1";
import { conversationPaths } from "@/app/api/v1";
import type {
  Conversation,
  ConversationCreateInput,
  ConversationListParams,
  ConversationUpdateInput,
  TurnListParams,
  TurnRequestInput,
  TurnResponse,
} from "./types";

export type RequestSignalOptions = {
  signal?: AbortSignal;
};

export async function listConversations(
  client: V1Client,
  workspaceId: string,
  params: ConversationListParams = {},
  options: RequestSignalOptions = {},
): Promise<Conversation[]> {
  const { limit = 20, offset = 0 } = params;
  return client.get<Conversation[]>(conversationPaths.list(workspaceId), {
    searchParams: { limit, offset },
    signal: options.signal,
  });
}

export async function getConversation(
  client: V1Client,
  workspaceId: string,
  conversationId: string,
  options: RequestSignalOptions = {},
): Promise<Conversation> {
  return client.get<Conversation>(
    conversationPaths.detail(workspaceId, conversationId),
    {
      signal: options.signal,
    },
  );
}

export async function createConversation(
  client: V1Client,
  workspaceId: string,
  input: ConversationCreateInput,
  options: RequestSignalOptions = {},
): Promise<Conversation> {
  const payload = {
    assistant_id: input.assistant_id,
    title: input.title?.trim() || "Hội thoại mới",
  };
  return client.post<Conversation>(
    conversationPaths.list(workspaceId),
    payload,
    {
      signal: options.signal,
    },
  );
}

export async function updateConversation(
  client: V1Client,
  workspaceId: string,
  conversationId: string,
  input: ConversationUpdateInput,
  options: RequestSignalOptions = {},
): Promise<Conversation> {
  const payload = {
    title: input.title.trim(),
    status: input.status,
  };
  return client.put<Conversation>(
    conversationPaths.detail(workspaceId, conversationId),
    payload,
    {
      signal: options.signal,
    },
  );
}

export async function listTurns(
  client: V1Client,
  workspaceId: string,
  conversationId: string,
  params: TurnListParams = {},
  options: RequestSignalOptions = {},
): Promise<TurnResponse[]> {
  const { limit = 50, offset = 0 } = params;
  return client.get<TurnResponse[]>(
    conversationPaths.turns(workspaceId, conversationId),
    {
      searchParams: { limit, offset },
      signal: options.signal,
    },
  );
}

export async function getTurn(
  client: V1Client,
  workspaceId: string,
  conversationId: string,
  turnId: string,
  options: RequestSignalOptions = {},
): Promise<TurnResponse> {
  return client.get<TurnResponse>(
    conversationPaths.turn(workspaceId, conversationId, turnId),
    {
      signal: options.signal,
    },
  );
}

export async function sendTurn(
  client: V1Client,
  workspaceId: string,
  conversationId: string,
  input: TurnRequestInput,
  idempotencyKey: string,
  options: RequestSignalOptions = {},
): Promise<TurnResponse> {
  const payload: {
    question: string;
    expected_turn_no: number;
    metadata_filter?: Record<string, unknown>;
  } = {
    question: input.question.trim(),
    expected_turn_no: input.expected_turn_no,
  };
  // Omitted (not `null`) keeps the backend inheritance rule: assistant policy
  // plus the last completed turn's scope.
  if (input.metadata_filter && Object.keys(input.metadata_filter).length > 0) {
    payload.metadata_filter = input.metadata_filter;
  }
  return client.post<TurnResponse>(
    conversationPaths.turns(workspaceId, conversationId),
    payload,
    {
      idempotencyKey,
      signal: options.signal,
    },
  );
}
