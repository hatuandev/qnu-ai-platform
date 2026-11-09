import { create } from "zustand";

export type Theme = "light" | "dark" | "system";

export type UiState = {
  theme: Theme;
  sidebarCollapsed: boolean;
  activeWorkspaceId: string | null;
  setTheme: (theme: Theme) => void;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setActiveWorkspaceId: (id: string | null) => void;
};

function getInitialTheme(): Theme {
  if (typeof window === "undefined") return "light";
  const saved = localStorage.getItem("qnu-ui-theme") as Theme | null;
  if (saved === "light" || saved === "dark") return saved;
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

export const useUiStore = create<UiState>((set) => ({
  theme: getInitialTheme(),
  sidebarCollapsed: false,
  activeWorkspaceId: null,
  setTheme: (theme) => {
    localStorage.setItem("qnu-ui-theme", theme);
    if (typeof document !== "undefined") {
      const isDark =
        theme === "dark" ||
        (theme === "system" &&
          window.matchMedia("(prefers-color-scheme: dark)").matches);
      document.documentElement.classList.toggle("dark", isDark);
    }
    set({ theme });
  },
  toggleSidebar: () =>
    set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  setSidebarCollapsed: (sidebarCollapsed) => set({ sidebarCollapsed }),
  setActiveWorkspaceId: (activeWorkspaceId) => set({ activeWorkspaceId }),
}));
