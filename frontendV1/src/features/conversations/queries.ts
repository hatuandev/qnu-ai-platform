import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useEffect } from "react";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import {
  createConversation,
  getConversation,
  getTurn,
  listConversations,
  listTurns,
  sendTurn,
  updateConversation,
} from "./requests";
import type {
  Conversation,
  ConversationCreateInput,
  ConversationListParams,
  ConversationUpdateInput,
  TurnListParams,
  TurnRequestInput,
  TurnResponse,
} from "./types";

export const conversationsQueryKeys = {
  root: (sessionId: number, workspaceId: string) => [
    "v1",
    sessionId,
    "workspaces",
    workspaceId,
    "conversations",
  ],
  list: (
    sessionId: number,
    workspaceId: string,
    params?: ConversationListParams,
  ) => [
    ...conversationsQueryKeys.root(sessionId, workspaceId),
    "list",
    params ?? {},
  ],
  detail: (sessionId: number, workspaceId: string, conversationId: string) => [
    ...conversationsQueryKeys.root(sessionId, workspaceId),
    "detail",
    conversationId,
  ],
  turns: (
    sessionId: number,
    workspaceId: string,
    conversationId: string,
    params?: TurnListParams,
  ) => [
    ...conversationsQueryKeys.detail(sessionId, workspaceId, conversationId),
    "turns",
    params ?? {},
  ],
  turn: (
    sessionId: number,
    workspaceId: string,
    conversationId: string,
    turnId: string,
  ) => [
    ...conversationsQueryKeys.detail(sessionId, workspaceId, conversationId),
    "turns",
    "item",
    turnId,
  ],
};

export function useConversationsQuery(
  workspaceId: string,
  params: ConversationListParams = {},
) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: conversationsQueryKeys.list(sessionId, workspaceId, params),
    queryFn: ({ signal }) =>
      listConversations(v1Client, workspaceId, params, { signal }),
    enabled: Boolean(workspaceId),
    staleTime: 10_000,
  });
}

export function useConversationQuery(
  workspaceId: string,
  conversationId: string,
) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: conversationsQueryKeys.detail(
      sessionId,
      workspaceId,
      conversationId,
    ),
    queryFn: ({ signal }) =>
      getConversation(v1Client, workspaceId, conversationId, { signal }),
    enabled: Boolean(workspaceId && conversationId),
    staleTime: 5_000,
  });
}

export function useTurnsQuery(
  workspaceId: string,
  conversationId: string,
  params: TurnListParams = {},
  options: { enabled?: boolean; refetchInterval?: number | false } = {},
) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: conversationsQueryKeys.turns(
      sessionId,
      workspaceId,
      conversationId,
      params,
    ),
    queryFn: ({ signal }) =>
      listTurns(v1Client, workspaceId, conversationId, params, { signal }),
    enabled: Boolean(
      workspaceId && conversationId && options.enabled !== false,
    ),
    staleTime: 5_000,
    refetchInterval: options.refetchInterval ?? false,
  });
}

export function useConversationHistoryQuery(
  workspaceId: string,
  conversationId: string,
  lastTurnNo: number | undefined,
) {
  const { sessionId } = useV1Auth();
  const queryClient = useQueryClient();
  const queryKey = [
    ...conversationsQueryKeys.detail(sessionId, workspaceId, conversationId),
    "history",
  ];
  const query = useInfiniteQuery({
    queryKey,
    enabled: Boolean(workspaceId && conversationId && lastTurnNo !== undefined),
    initialPageParam: 0,
    queryFn: async ({ pageParam, signal }) => {
      // The server orders turns ascending. Page zero is the newest window.
      const end = Math.max(0, (lastTurnNo ?? 0) - pageParam * 50);
      const offset = Math.max(0, end - 50);
      const items = await listTurns(
        v1Client,
        workspaceId,
        conversationId,
        {
          offset,
          limit: Math.max(1, end - offset),
        },
        { signal },
      );
      return { items, offset };
    },
    getNextPageParam: (lastPage, pages) =>
      lastPage.offset > 0 ? pages.length : undefined,
    select: (data) => ({
      ...data,
      turns: [
        ...new Map(
          data.pages.flatMap((p) => p.items).map((t) => [t.id, t]),
        ).values(),
      ].sort((a, b) => a.turn_no - b.turn_no),
    }),
  });
  useEffect(() => {
    if (lastTurnNo !== undefined) {
      void queryClient.invalidateQueries({
        queryKey: [
          ...conversationsQueryKeys.detail(
            sessionId,
            workspaceId,
            conversationId,
          ),
          "history",
        ],
      });
    }
  }, [queryClient, workspaceId, conversationId, sessionId, lastTurnNo]);
  return query;
}

export function useTurnQuery(
  workspaceId: string,
  conversationId: string,
  turnId: string,
  options: { enabled?: boolean; refetchInterval?: number | false } = {},
) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: conversationsQueryKeys.turn(
      sessionId,
      workspaceId,
      conversationId,
      turnId,
    ),
    queryFn: ({ signal }) =>
      getTurn(v1Client, workspaceId, conversationId, turnId, { signal }),
    enabled: Boolean(
      workspaceId && conversationId && turnId && options.enabled !== false,
    ),
    staleTime: 3_000,
    refetchInterval: options.refetchInterval ?? false,
  });
}

export function useCreateConversation(workspaceId: string) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();

  return useMutation({
    mutationFn: (input: ConversationCreateInput) =>
      createConversation(v1Client, workspaceId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: conversationsQueryKeys.root(sessionId, workspaceId),
      });
    },
  });
}

export function useUpdateConversation(
  workspaceId: string,
  conversationId: string,
) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();

  return useMutation({
    mutationFn: (input: ConversationUpdateInput) =>
      updateConversation(v1Client, workspaceId, conversationId, input),
    onSuccess: (updated: Conversation) => {
      queryClient.setQueryData(
        conversationsQueryKeys.detail(sessionId, workspaceId, conversationId),
        updated,
      );
      void queryClient.invalidateQueries({
        queryKey: conversationsQueryKeys.root(sessionId, workspaceId),
      });
    },
  });
}

export function useSendTurn(workspaceId: string, conversationId: string) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();

  return useMutation({
    mutationFn: ({
      input,
      idempotencyKey,
    }: {
      input: TurnRequestInput;
      idempotencyKey: string;
    }) =>
      sendTurn(v1Client, workspaceId, conversationId, input, idempotencyKey),
    onSuccess: (newTurn: TurnResponse) => {
      const detail = conversationsQueryKeys.detail(
        sessionId,
        workspaceId,
        conversationId,
      );
      queryClient.setQueryData<Conversation>(detail, (current) =>
        current && newTurn.turn_no > current.last_turn_no
          ? { ...current, last_turn_no: newTurn.turn_no }
          : current,
      );
      void queryClient.invalidateQueries({
        queryKey: detail,
      });
      return newTurn;
    },
  });
}
