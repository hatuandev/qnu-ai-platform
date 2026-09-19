import { type EventSourceMessage, createParser } from "eventsource-parser";
import { useCallback, useEffect, useRef, useState } from "react";

export interface ChatCitation {
  id: string;
  title: string;
  document_name: string;
  clause?: string;
  article?: string;
  page?: number;
  score?: number;
  excerpt: string;
  url?: string;
}

export interface ChatAttachment {
  id: string;
  name: string;
  size: number;
  type: string;
  url?: string;
  ocrStatus?: "idle" | "processing" | "completed" | "failed";
  textContent?: string;
}

export interface ChatMessageItem {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  status?: "streaming" | "completed" | "error";
  timestamp: string;
  citations?: ChatCitation[];
  suggestedQuestions?: string[];
  attachments?: ChatAttachment[];
  artifacts?: ChatAttachment[];
  latencyMs?: number;
}

export interface UseRAGStreamOptions {
  assistantCode?: string;
  tenantId?: string;
  conversationId?: string;
  initialMessages?: ChatMessageItem[];
  onFinish?: (message: ChatMessageItem) => void;
  onError?: (err: Error) => void;
}

export function useRAGStream(options: UseRAGStreamOptions = {}) {
  const {
    assistantCode = "admissions",
    tenantId = "tenant_qnu",
    conversationId,
    initialMessages = [],
    onFinish,
    onError,
  } = options;

  const [messages, setMessages] = useState<ChatMessageItem[]>(initialMessages);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [activeCitation, setActiveCitation] = useState<ChatCitation | null>(null);
  const [currentConversationId, setCurrentConversationId] = useState<string | undefined>(
    conversationId
  );

  useEffect(() => {
    if (conversationId) {
      setCurrentConversationId(conversationId);
    }
  }, [conversationId]);

  const abortControllerRef = useRef<AbortController | null>(null);

  // Clean up controller on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const stopStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  const clearMessages = useCallback(() => {
    stopStreaming();
    setMessages([]);
    setError(null);
    setActiveCitation(null);
    setCurrentConversationId(undefined);
  }, [stopStreaming]);

  const sendMessage = useCallback(
    async (prompt: string, attachments?: ChatAttachment[]) => {
      const trimmed = prompt.trim();
      if (!trimmed && (!attachments || attachments.length === 0)) return;

      stopStreaming();
      setError(null);

      const userMessageId = `usr_${Date.now()}`;
      const assistantMessageId = `ast_${Date.now() + 1}`;
      const startTime = performance.now();

      const newUserMessage: ChatMessageItem = {
        id: userMessageId,
        role: "user",
        content: trimmed,
        status: "completed",
        timestamp: new Date().toLocaleTimeString("vi-VN", {
          hour: "2-digit",
          minute: "2-digit",
        }),
        attachments,
      };

      const newAssistantPlaceholder: ChatMessageItem = {
        id: assistantMessageId,
        role: "assistant",
        content: "",
        status: "streaming",
        timestamp: new Date().toLocaleTimeString("vi-VN", {
          hour: "2-digit",
          minute: "2-digit",
        }),
      };

      setMessages((prev) => [...prev, newUserMessage, newAssistantPlaceholder]);
      setIsStreaming(true);

      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        const response = await fetch(`/platform/v1alpha1/assistants/${assistantCode}/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "text/event-stream, application/json",
          },
          body: JSON.stringify({
            message: trimmed,
            conversation_id: currentConversationId || conversationId,
            tenant_id: tenantId,
            stream: true,
            attachments: (attachments || []).map((a) => ({
              id: a.id,
              name: a.name,
              size: a.size,
              type: a.type,
              text_content: a.textContent,
            })),
          }),
          signal: controller.signal,
        });

        if (!response.ok) {
          let errorDetail = `Lỗi kết nối máy chủ (HTTP ${response.status})`;
          try {
            const errJson = await response.json();
            if (errJson.detail) {
              errorDetail = errJson.detail;
            } else if (errJson.title) {
              errorDetail = errJson.title;
            }
          } catch {
            // keep default error detail
          }
          throw new Error(errorDetail);
        }

        const contentType = response.headers.get("content-type") || "";

        // Real Server-Sent Events (SSE) stream processing
        if (contentType.includes("text/event-stream") && response.body) {
          const reader = response.body.getReader();
          const decoder = new TextDecoder("utf-8");
          let accumulatedContent = "";
          const finalCitations: ChatCitation[] = [];
          const finalArtifacts: ChatAttachment[] = [];
          let finalSuggestions: string[] = [];

          const parser = createParser({
            onEvent: (event: EventSourceMessage) => {
              if (event.event === "token" || !event.event) {
                try {
                  const parsed = JSON.parse(event.data);
                  if (parsed.delta) {
                    accumulatedContent += parsed.delta;
                  } else if (parsed.text) {
                    accumulatedContent += parsed.text;
                  }
                } catch {
                  accumulatedContent += event.data;
                }
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMessageId ? { ...msg, content: accumulatedContent } : msg
                  )
                );
              } else if (event.event === "citation") {
                try {
                  const citationObj = JSON.parse(event.data);
                  finalCitations.push({
                    id:
                      citationObj.id ||
                      citationObj.source_id ||
                      `cite_${finalCitations.length + 1}`,
                    title: citationObj.title || citationObj.source || "Văn bản trích dẫn",
                    document_name: citationObj.document_name || "Tai_lieu_chinh_thuc.pdf",
                    clause: citationObj.clause,
                    article: citationObj.article,
                    page: citationObj.page ?? citationObj.page_number,
                    score: citationObj.score ?? 0.95,
                    excerpt: citationObj.excerpt || citationObj.quote || citationObj.content || "",
                    url: citationObj.url,
                  });
                } catch {
                  // ignore malformed citation chunk
                }
              } else if (event.event === "artifact") {
                try {
                  const artObj = JSON.parse(event.data);
                  finalArtifacts.push({
                    id: artObj.id || `art_${finalArtifacts.length + 1}`,
                    name: artObj.name || `qnu_van_ban.${artObj.type || "docx"}`,
                    size: typeof artObj.size === "number" ? artObj.size : 0,
                    type: artObj.type || "docx",
                    url: artObj.url || "",
                  });
                } catch {
                  // ignore malformed artifact chunk
                }
              } else if (event.event === "status") {
                try {
                  const statusObj = JSON.parse(event.data);
                  if (statusObj.conversation_id) {
                    setCurrentConversationId(statusObj.conversation_id);
                  }
                } catch {
                  // ignore status payload error
                }
              } else if (event.event === "done" || event.event === "end") {
                try {
                  const doneData = JSON.parse(event.data);
                  if (doneData.suggested_questions && Array.isArray(doneData.suggested_questions)) {
                    finalSuggestions = doneData.suggested_questions;
                  }
                  if (doneData.conversation_id) {
                    setCurrentConversationId(doneData.conversation_id);
                  }
                } catch {
                  // ignore
                }
              } else if (event.event === "error") {
                try {
                  const errPayload = JSON.parse(event.data);
                  throw new Error(errPayload.error || "Lỗi xử lý luồng AI");
                } catch {
                  throw new Error(event.data || "Lỗi xử lý luồng AI");
                }
              }
            },
          });

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            parser.feed(chunk);
          }

          const latencyMs = Math.round(performance.now() - startTime);
          const finalMsg: ChatMessageItem = {
            id: assistantMessageId,
            role: "assistant",
            content: accumulatedContent || "Đã nhận được phản hồi từ hệ thống.",
            status: "completed",
            timestamp: new Date().toLocaleTimeString("vi-VN", {
              hour: "2-digit",
              minute: "2-digit",
            }),
            citations: finalCitations,
            artifacts: finalArtifacts,
            suggestedQuestions: finalSuggestions,
            latencyMs,
          };

          setMessages((prev) =>
            prev.map((msg) => (msg.id === assistantMessageId ? finalMsg : msg))
          );
          setIsStreaming(false);
          if (onFinish) onFinish(finalMsg);
        } else {
          // Standard JSON response fallback (when stream=false or non-SSE)
          const data = await response.json();
          if (data.conversation_id) {
            setCurrentConversationId(data.conversation_id);
          }
          const latencyMs = data.latency_ms || Math.round(performance.now() - startTime);
          const answer = data.answer || "Đã xử lý xong yêu cầu của bạn.";
          const citations: ChatCitation[] = (data.citations || []).map(
            (c: Record<string, unknown>, idx: number) => ({
              id: (c.id as string) || (c.source_id as string) || `cite_${idx + 1}`,
              title: (c.title as string) || (c.source as string) || "Văn bản trích dẫn",
              document_name: (c.document_name as string) || "Tai_lieu_chinh_thuc.pdf",
              clause: c.clause as string | undefined,
              article: c.article as string | undefined,
              page:
                typeof c.page === "number"
                  ? c.page
                  : typeof c.page_number === "number"
                    ? c.page_number
                    : undefined,
              score: typeof c.score === "number" ? c.score : 0.95,
              excerpt: (c.excerpt as string) || (c.quote as string) || (c.content as string) || "",
              url: c.url as string | undefined,
            })
          );

          const artifacts: ChatAttachment[] = (data.artifacts || []).map(
            (art: Record<string, unknown>, idx: number) => ({
              id: (art.id as string) || `art_${idx + 1}`,
              name: (art.name as string) || `qnu_van_ban.${art.type || "docx"}`,
              size: typeof art.size === "number" ? art.size : 0,
              type: (art.type as string) || "docx",
              url: (art.url as string) || "",
            })
          );

          const finalMsg: ChatMessageItem = {
            id: assistantMessageId,
            role: "assistant",
            content: answer,
            status: "completed",
            timestamp: new Date().toLocaleTimeString("vi-VN", {
              hour: "2-digit",
              minute: "2-digit",
            }),
            citations,
            artifacts,
            suggestedQuestions: data.suggested_questions || [],
            latencyMs,
          };

          setMessages((prev) =>
            prev.map((msg) => (msg.id === assistantMessageId ? finalMsg : msg))
          );
          setIsStreaming(false);
          if (onFinish) onFinish(finalMsg);
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name === "AbortError") {
          setIsStreaming(false);
          return;
        }

        const errorMessage =
          err instanceof Error
            ? err.message
            : "Không thể kết nối đến máy chủ Trợ lý AI QNU. Vui lòng kiểm tra lại dịch vụ backend.";

        const errorMsgItem: ChatMessageItem = {
          id: assistantMessageId,
          role: "assistant",
          content: `⚠️ ${errorMessage}`,
          status: "error",
          timestamp: new Date().toLocaleTimeString("vi-VN", {
            hour: "2-digit",
            minute: "2-digit",
          }),
        };

        setMessages((prev) =>
          prev.map((msg) => (msg.id === assistantMessageId ? errorMsgItem : msg))
        );
        setError(errorMessage);
        setIsStreaming(false);
        if (onError && err instanceof Error) onError(err);
      } finally {
        abortControllerRef.current = null;
      }
    },
    [
      assistantCode,
      conversationId,
      currentConversationId,
      tenantId,
      stopStreaming,
      onFinish,
      onError,
    ]
  );

  return {
    messages,
    setMessages,
    isStreaming,
    error,
    activeCitation,
    setActiveCitation,
    conversationId: currentConversationId,
    sendMessage,
    stopStreaming,
    clearMessages,
  };
}
