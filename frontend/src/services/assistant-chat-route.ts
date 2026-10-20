/** Only authorized admin callers opt in; the server verifies debug permission. */
export function assistantChatUrl(code: string, debug = false): string {
  return `/platform/v1alpha1/assistants/${encodeURIComponent(code)}/chat${debug ? "?debug=true" : ""}`;
}

export interface ConversationSession {
  conversationId: string;
  conversationToken: string;
}

export function ownedConversationSession(
  thread: {
    assistantCode: string;
    runtimeSession?: ConversationSession;
  } | null,
  assistantCode: string,
): ConversationSession | undefined {
  if (thread?.assistantCode !== assistantCode) return undefined;
  const session = thread.runtimeSession;
  return session?.conversationId && session.conversationToken
    ? session
    : undefined;
}
