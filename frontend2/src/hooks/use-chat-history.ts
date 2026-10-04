import { useCallback, useEffect, useMemo, useState } from "react";
import type { ChatMessageItem } from "./use-rag-stream";

export interface ChatThread {
  id: string;
  assistantCode: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  messages: ChatMessageItem[];
}

export interface GroupedChatThreads {
  today: ChatThread[];
  yesterday: ChatThread[];
  last7Days: ChatThread[];
  older: ChatThread[];
}

function getStorageKey(assistantCode: string): string {
  return `qnu_chat_threads_${assistantCode.toLowerCase()}`;
}

function generateThreadTitle(userPrompt: string): string {
  const clean = userPrompt.replace(/\s+/g, " ").trim();
  if (!clean) return "Đoạn chat mới";
  if (clean.length <= 42) return clean;
  const truncated = clean.slice(0, 40);
  const lastSpace = truncated.lastIndexOf(" ");
  return lastSpace > 20
    ? `${truncated.slice(0, lastSpace)}...`
    : `${truncated}...`;
}

function createNewThreadObject(assistantCode: string): ChatThread {
  const now = Date.now();
  const id = `thr_${now}_${Math.random().toString(36).slice(2, 8)}`;
  return {
    id,
    assistantCode,
    title: "Đoạn chat mới",
    createdAt: now,
    updatedAt: now,
    messages: [],
  };
}

export function useChatHistory(assistantCode: string) {
  const storageKey = useMemo(
    () => getStorageKey(assistantCode),
    [assistantCode],
  );

  // Load threads from localStorage
  const [threads, setThreads] = useState<ChatThread[]>(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) {
          return parsed.sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
        }
      }
    } catch (e) {
      console.warn("Failed to load chat history from localStorage", e);
    }
    return [];
  });

  // Current active thread id
  const [currentThreadId, setCurrentThreadId] = useState<string>(() => {
    return threads.length > 0 ? threads[0].id : "";
  });

  // Reload threads when assistantCode changes
  useEffect(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) {
          const sorted = parsed.sort(
            (a, b) => (b.updatedAt || 0) - (a.updatedAt || 0),
          );
          setThreads(sorted);
          if (sorted.length > 0) {
            setCurrentThreadId(sorted[0].id);
            return;
          }
        }
      }
    } catch {
      // ignore
    }
    setThreads([]);
    setCurrentThreadId("");
  }, [storageKey]);

  // Persist threads to localStorage whenever they change
  const persistThreads = useCallback(
    (newThreads: ChatThread[]) => {
      try {
        localStorage.setItem(storageKey, JSON.stringify(newThreads));
      } catch (e) {
        console.warn("Failed to save chat history to localStorage", e);
      }
    },
    [storageKey],
  );

  // Get current active thread
  const currentThread = useMemo(() => {
    return threads.find((t) => t.id === currentThreadId) || null;
  }, [threads, currentThreadId]);

  // Create a brand new thread
  const createNewThread = useCallback((): ChatThread => {
    const freshThread = createNewThreadObject(assistantCode);
    setThreads((prev) => {
      const updated = [freshThread, ...prev];
      persistThreads(updated);
      return updated;
    });
    setCurrentThreadId(freshThread.id);
    return freshThread;
  }, [assistantCode, persistThreads]);

  // Select a thread by id
  const selectThread = useCallback(
    (threadId: string) => {
      const found = threads.find((t) => t.id === threadId);
      if (found) {
        setCurrentThreadId(threadId);
      }
    },
    [threads],
  );

  // Update messages of a thread (and auto-name title if it's new)
  const saveThreadMessages = useCallback(
    (threadId: string, messages: ChatMessageItem[]) => {
      setThreads((prev) => {
        const targetIndex = prev.findIndex((t) => t.id === threadId);
        let updatedThreads: ChatThread[];

        if (targetIndex >= 0) {
          const target = prev[targetIndex];
          let title = target.title;

          // Auto-generate title from first user message if title is default
          if ((!title || title === "Đoạn chat mới") && messages.length > 0) {
            const firstUserMsg = messages.find((m) => m.role === "user");
            if (firstUserMsg?.content) {
              title = generateThreadTitle(firstUserMsg.content);
            }
          }

          const updatedTarget: ChatThread = {
            ...target,
            title,
            messages,
            updatedAt: Date.now(),
          };

          updatedThreads = [
            updatedTarget,
            ...prev.filter((_, idx) => idx !== targetIndex),
          ];
        } else {
          // If thread does not exist yet in list, create it
          let title = "Đoạn chat mới";
          const firstUserMsg = messages.find((m) => m.role === "user");
          if (firstUserMsg?.content) {
            title = generateThreadTitle(firstUserMsg.content);
          }

          const newThread: ChatThread = {
            id: threadId,
            assistantCode,
            title,
            createdAt: Date.now(),
            updatedAt: Date.now(),
            messages,
          };
          updatedThreads = [newThread, ...prev];
        }

        persistThreads(updatedThreads);
        return updatedThreads;
      });
    },
    [assistantCode, persistThreads],
  );

  // Rename a thread
  const renameThread = useCallback(
    (threadId: string, newTitle: string) => {
      const trimmed = newTitle.trim();
      if (!trimmed) return;

      setThreads((prev) => {
        const updated = prev.map((t) =>
          t.id === threadId
            ? { ...t, title: trimmed, updatedAt: Date.now() }
            : t,
        );
        persistThreads(updated);
        return updated;
      });
    },
    [persistThreads],
  );

  // Delete a thread
  const deleteThread = useCallback(
    (threadId: string) => {
      setThreads((prev) => {
        const remaining = prev.filter((t) => t.id !== threadId);
        persistThreads(remaining);

        if (currentThreadId === threadId) {
          if (remaining.length > 0) {
            setCurrentThreadId(remaining[0].id);
          } else {
            setCurrentThreadId("");
          }
        }
        return remaining;
      });
    },
    [currentThreadId, persistThreads],
  );

  // Clear all threads for this assistant
  const clearAllThreads = useCallback(() => {
    try {
      localStorage.removeItem(storageKey);
    } catch {
      // ignore
    }
    setThreads([]);
    setCurrentThreadId("");
  }, [storageKey]);

  // Group threads by relative date
  const groupedThreads = useMemo<GroupedChatThreads>(() => {
    const now = new Date();
    const startOfToday = new Date(
      now.getFullYear(),
      now.getMonth(),
      now.getDate(),
    ).getTime();
    const startOfYesterday = startOfToday - 24 * 60 * 60 * 1000;
    const startOf7Days = startOfToday - 7 * 24 * 60 * 60 * 1000;

    const groups: GroupedChatThreads = {
      today: [],
      yesterday: [],
      last7Days: [],
      older: [],
    };

    for (const thread of threads) {
      const time = thread.updatedAt || thread.createdAt || 0;
      if (time >= startOfToday) {
        groups.today.push(thread);
      } else if (time >= startOfYesterday) {
        groups.yesterday.push(thread);
      } else if (time >= startOf7Days) {
        groups.last7Days.push(thread);
      } else {
        groups.older.push(thread);
      }
    }

    return groups;
  }, [threads]);

  return {
    threads,
    currentThreadId,
    currentThread,
    groupedThreads,
    createNewThread,
    selectThread,
    saveThreadMessages,
    renameThread,
    deleteThread,
    clearAllThreads,
  };
}
