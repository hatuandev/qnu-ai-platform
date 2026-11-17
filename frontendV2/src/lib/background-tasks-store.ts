import { create } from "zustand";
import { persist } from "zustand/middleware";

export type BackgroundTaskKind = "preparation" | "lifecycle";

export type BackgroundTaskStatus =
  | "queued"
  | "waiting_ocr"
  | "compiling"
  | "ready"
  | "failed"
  | "uncertain"
  | "cancelled";

export type BackgroundTask = {
  id: string; // intentId or actionId
  kind: BackgroundTaskKind;
  workspaceId: string;
  collectionId: string;
  sourceId: string;
  sourceTitle: string;
  fileName: string;
  status: BackgroundTaskStatus;
  step: string;
  errorCode: string | null;
  createdAt: string;
  startedAt?: string | null;
  finishedAt?: string | null;
  durationMs?: number | null;
  isDismissed?: boolean;
};

type BackgroundTasksState = {
  tasks: BackgroundTask[];
  isExpanded: boolean;
  registerPreparationTask: (task: {
    id: string;
    workspaceId: string;
    collectionId: string;
    sourceId: string;
    sourceTitle: string;
    fileName: string;
  }) => void;
  updateTaskStatus: (
    id: string,
    update: {
      status?: BackgroundTaskStatus;
      step?: string;
      errorCode?: string | null;
      startedAt?: string | null;
      finishedAt?: string | null;
      durationMs?: number | null;
    },
  ) => void;
  dismissTask: (id: string) => void;
  clearCompleted: () => void;
  toggleExpanded: () => void;
  setExpanded: (expanded: boolean) => void;
};

export const useBackgroundTasksStore = create<BackgroundTasksState>()(
  persist(
    (set) => ({
      tasks: [],
      isExpanded: true,

      registerPreparationTask: (item) =>
        set((state) => {
          // Avoid duplicate entry
          const existing = state.tasks.find((t) => t.id === item.id);
          if (existing) {
            return {
              tasks: state.tasks.map((t) =>
                t.id === item.id ? { ...t, isDismissed: false } : t,
              ),
              isExpanded: true,
            };
          }
          const newTask: BackgroundTask = {
            id: item.id,
            kind: "preparation",
            workspaceId: item.workspaceId,
            collectionId: item.collectionId,
            sourceId: item.sourceId,
            sourceTitle: item.sourceTitle,
            fileName: item.fileName,
            status: "queued",
            step: "Đã nhận yêu cầu",
            errorCode: null,
            createdAt: new Date().toISOString(),
            isDismissed: false,
          };
          return {
            tasks: [newTask, ...state.tasks.slice(0, 19)], // keep last 20
            isExpanded: true,
          };
        }),

      updateTaskStatus: (id, update) =>
        set((state) => ({
          tasks: state.tasks.map((t) =>
            t.id === id
              ? {
                  ...t,
                  status: update.status ?? t.status,
                  step: update.step ?? t.step,
                  errorCode:
                    update.errorCode !== undefined
                      ? update.errorCode
                      : t.errorCode,
                  startedAt:
                    update.startedAt !== undefined
                      ? update.startedAt
                      : t.startedAt,
                  finishedAt:
                    update.finishedAt !== undefined
                      ? update.finishedAt
                      : t.finishedAt,
                  durationMs:
                    update.durationMs !== undefined
                      ? update.durationMs
                      : t.durationMs,
                }
              : t,
          ),
        })),

      dismissTask: (id) =>
        set((state) => ({
          tasks: state.tasks.map((t) =>
            t.id === id ? { ...t, isDismissed: true } : t,
          ),
        })),

      clearCompleted: () =>
        set((state) => ({
          tasks: state.tasks.filter(
            (t) =>
              t.status !== "ready" &&
              t.status !== "failed" &&
              t.status !== "cancelled",
          ),
        })),

      toggleExpanded: () => set((state) => ({ isExpanded: !state.isExpanded })),
      setExpanded: (expanded) => set({ isExpanded: expanded }),
    }),
    {
      name: "qnu_background_tasks_v2",
      partialize: (state) => ({
        // Only persist non-sensitive tracking references (IDs & titles)
        tasks: state.tasks.slice(0, 10),
      }),
    },
  ),
);
