/**
 * HTTP request functions for the Publications domain.
 * Admin calls use `v1Client` (authenticated); anonymous chatbot calls use
 * `v1PublicClient` so no session token is ever attached to a public link.
 */

import { v1Client, v1PublicClient } from "../v1-client";
import { publicationPaths } from "./endpoints";
import type {
  PublicationResponse,
  PublicationStats,
  PublicationUpdateRequest,
  PublicChatbotInfo,
  PublicChatbotList,
  PublicChatSession,
  PublicTurnRequest,
  PublicTurnResponse,
} from "./types";

export async function getPublication(
  workspaceId: string,
  assistantId: string,
  options?: { signal?: AbortSignal },
): Promise<PublicationResponse> {
  return v1Client.get<PublicationResponse>(
    publicationPaths.admin(workspaceId, assistantId),
    options,
  );
}

export async function savePublication(
  workspaceId: string,
  assistantId: string,
  data: PublicationUpdateRequest,
  options?: { signal?: AbortSignal },
): Promise<PublicationResponse> {
  return v1Client.put<PublicationResponse>(
    publicationPaths.admin(workspaceId, assistantId),
    data,
    options,
  );
}

export async function getPublicationStats(
  workspaceId: string,
  assistantId: string,
  days: number,
  options?: { signal?: AbortSignal },
): Promise<PublicationStats> {
  return v1Client.get<PublicationStats>(
    publicationPaths.adminStats(workspaceId, assistantId, days),
    options,
  );
}

export async function getPublicChatbotList(options?: {
  signal?: AbortSignal;
}): Promise<PublicChatbotList> {
  return v1PublicClient.get<PublicChatbotList>(
    publicationPaths.publicList,
    options,
  );
}

export async function getPublicChatbotInfo(
  slug: string,
  options?: { signal?: AbortSignal },
): Promise<PublicChatbotInfo> {
  return v1PublicClient.get<PublicChatbotInfo>(
    publicationPaths.publicInfo(slug),
    options,
  );
}

export async function createPublicChatSession(
  slug: string,
  options?: { signal?: AbortSignal },
): Promise<PublicChatSession> {
  return v1PublicClient.post<PublicChatSession>(
    publicationPaths.publicSessions(slug),
    undefined,
    options,
  );
}

export async function sendPublicTurn(
  slug: string,
  data: PublicTurnRequest,
  options?: { signal?: AbortSignal },
): Promise<PublicTurnResponse> {
  return v1PublicClient.post<PublicTurnResponse>(
    publicationPaths.publicTurns(slug),
    data,
    options,
  );
}
