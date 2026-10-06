import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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

export function generateThreadTitle(userPrompt: string): string {
  const clean = userPrompt.replace(/\s+/g, " ").trim();
  if (!clean) return "Đoạn chat mới";
  if (clean.length <= 42) return clean;
  const truncated = clean.slice(0, 40);
  const lastSpace = truncated.lastIndexOf(" ");
  return lastSpace > 20
    ? `${truncated.slice(0, lastSpace)}...`
    : `${truncated}...`;
}

function createNewThreadObject(
  assistantCode: string,
  initialTitle?: string,
): ChatThread {
  const now = Date.now();
  const id = `thr_${now}_${Math.random().toString(36).slice(2, 8)}`;
  return {
    id,
    assistantCode,
    title: initialTitle ? generateThreadTitle(initialTitle) : "Đoạn chat mới",
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

  // Load threads from localStorage lazily
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

  const activeKeyRef = useRef(storageKey);

  // Sync threads to localStorage and reload when storageKey changes
  useEffect(() => {
    if (activeKeyRef.current !== storageKey) {
      activeKeyRef.current = storageKey;
      try {
        const saved = localStorage.getItem(storageKey);
        if (saved) {
          const parsed = JSON.parse(saved);
          if (Array.isArray(parsed)) {
            const sorted = parsed.sort(
              (a, b) => (b.updatedAt || 0) - (a.updatedAt || 0),
            );
            setThreads(sorted);
            setCurrentThreadId(sorted.length > 0 ? sorted[0].id : "");
            return;
          }
        }
      } catch {
        // ignore
      }
      setThreads([]);
      setCurrentThreadId("");
      return;
    }

    // Persist to localStorage whenever threads change for current storageKey
    try {
      localStorage.setItem(storageKey, JSON.stringify(threads));
    } catch (e) {
      console.warn("Failed to save chat history to localStorage", e);
    }
  }, [threads, storageKey]);

  // Get current active thread
  const currentThread = useMemo(() => {
    return threads.find((t) => t.id === currentThreadId) || null;
  }, [threads, currentThreadId]);

  // Create a brand new thread (with optional initial title)
  const createNewThread = useCallback(
    (initialPrompt?: string): ChatThread => {
      const freshThread = createNewThreadObject(assistantCode, initialPrompt);
      setThreads((prev) => [freshThread, ...prev]);
      setCurrentThreadId(freshThread.id);
      return freshThread;
    },
    [assistantCode],
  );

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

  // Update messages of a thread (and auto-name title if it's default)
  const saveThreadMessages = useCallback(
    (threadId: string, messages: ChatMessageItem[]) => {
      if (!threadId) return;

      setThreads((prev) => {
        const targetIndex = prev.findIndex((t) => t.id === threadId);

        let autoTitle: string | undefined;
        const firstUserMsg = messages.find((m) => m.role === "user");
        if (firstUserMsg?.content) {
          autoTitle = generateThreadTitle(firstUserMsg.content);
        }

        if (targetIndex >= 0) {
          const target = prev[targetIndex];
          const finalTitle =
            target.title && target.title !== "Đoạn chat mới"
              ? target.title
              : autoTitle || target.title;

          const updatedTarget: ChatThread = {
            ...target,
            title: finalTitle,
            messages,
            updatedAt: Date.now(),
          };

          return [
            updatedTarget,
            ...prev.filter((_, idx) => idx !== targetIndex),
          ];
        }

        // Thread does not exist yet: create and insert at head
        const newThread: ChatThread = {
          id: threadId,
          assistantCode,
          title: autoTitle || "Đoạn chat mới",
          createdAt: Date.now(),
          updatedAt: Date.now(),
          messages,
        };
        return [newThread, ...prev];
      });
    },
    [assistantCode],
  );

  // Rename a thread
  const renameThread = useCallback((threadId: string, newTitle: string) => {
    const trimmed = newTitle.trim();
    if (!trimmed) return;

    setThreads((prev) =>
      prev.map((t) =>
        t.id === threadId ? { ...t, title: trimmed, updatedAt: Date.now() } : t,
      ),
    );
  }, []);

  // Delete a thread
  const deleteThread = useCallback((threadId: string) => {
    setThreads((prev) => {
      const remaining = prev.filter((t) => t.id !== threadId);
      return remaining;
    });

    setCurrentThreadId((prevId) => {
      if (prevId === threadId) {
        // Will be picked up or reset
        return "";
      }
      return prevId;
    });
  }, []);

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
