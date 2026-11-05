// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import type { ComponentProps } from "react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import type { CallerWorkspaceRole } from "@/app/auth/v1/permissions";
import { QnuSettingsHub } from "@/features/settings/qnu-settings-hub";
import {
  isPrimarySidebarFeatureActive,
  isSettingsRouteActive,
  workspaceFeatures,
} from "@/navigation/workspace-features";

const state = vi.hoisted(() => ({
  authenticated: true,
  pending: false,
  role: { kind: "platform-admin" } as CallerWorkspaceRole,
  scope: { workspaceId: "w", collectionId: "c" } as {
    workspaceId?: string;
    collectionId?: string;
  },
}));
vi.mock("@/app/auth/v1", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/app/auth/v1")>()),
  useV1Auth: () => ({
    actor: { roles: ["AI.Admin"] },
    isAuthenticated: state.authenticated,
  }),
}));
vi.mock("@/navigation/use-feature-scope", () => ({
  useFeatureScope: () => state.scope,
}));
vi.mock("@/features/workspaces/queries", () => ({
  useWorkspacesQuery: () => ({
    data: { items: [{ id: "w", name: "Đơn vị thử" }] },
  }),
  useWorkspaceQuery: () => ({ data: { id: "w", name: "Đơn vị thử" } }),
  useCallerWorkspaceRole: () => ({
    role: state.role,
    isPending: state.pending,
  }),
}));
vi.mock("@tanstack/react-router", () => ({
  Link: ({
    to,
    params,
    search,
    ...props
  }: ComponentProps<"a"> & {
    to: string;
    params?: Record<string, string>;
    search?: Record<string, unknown>;
  }) => {
    const path = to.replace(
      /\$(\w+)/g,
      (match, key: string) => params?.[key] ?? match,
    );
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(search ?? {})) {
      if (value !== undefined) query.set(key, String(value));
    }
    return <a {...props} href={`${path}${query.size ? `?${query}` : ""}`} />;
  },
}));
beforeEach(() => {
  state.authenticated = true;
  state.pending = false;
  state.role = { kind: "platform-admin" };
  state.scope = { workspaceId: "w", collectionId: "c" };
});
afterEach(cleanup);

test("settings opens evaluation for the selected collection without an index-management link", () => {
  render(<QnuSettingsHub />);
  expect(
    screen.getByRole("link", { name: "Đánh giá RAG" }).getAttribute("href"),
  ).toBe("/workspaces/w/collections/c/evaluations?page=1");
  expect(screen.queryByRole("link", { name: "Quản trị chỉ mục" })).toBeNull();
});

test("settings uses the existing collection chooser when no collection is selected", () => {
  state.scope = { workspaceId: "w" };
  render(<QnuSettingsHub />);
  expect(
    screen.getByRole("link", { name: "Đánh giá RAG" }).getAttribute("href"),
  ).toBe("/workspaces/choose/evaluation?workspaceId=w&page=1");
});

test("settings never attaches a collection without its workspace scope", () => {
  state.scope = { collectionId: "old-collection" };
  render(<QnuSettingsHub />);
  expect(
    screen.getByRole("link", { name: "Đánh giá RAG" }).getAttribute("href"),
  ).toBe("/workspaces/choose/evaluation?workspaceId=w&page=1");
});

test.each(["member", "reviewer"] as const)(
  "%s cannot access the evaluation entry",
  (role) => {
    state.role = { kind: "member", role };
    render(<QnuSettingsHub />);
    expect(screen.queryByRole("link", { name: "Đánh giá RAG" })).toBeNull();
  },
);

test.each(["pending", "anonymous"])(
  "evaluation entry waits for authorization: %s",
  (kind) => {
    state.pending = kind === "pending";
    state.authenticated = kind !== "anonymous";
    render(<QnuSettingsHub />);
    expect(screen.queryByRole("link", { name: "Đánh giá RAG" })).toBeNull();
  },
);

test("editor retains evaluation access in settings", () => {
  state.role = { kind: "member", role: "editor" };
  render(<QnuSettingsHub />);
  expect(screen.getByRole("link", { name: "Đánh giá RAG" })).toBeTruthy();
});

test.each([
  "/workspaces/choose/evaluation",
  "/workspaces/w/collections/c/evaluations",
])(
  "evaluation marks settings rather than the knowledge sidebar: %s",
  (path) => {
    expect(workspaceFeatures.evaluation.group).toBe("Cấu hình đơn vị");
    expect(isSettingsRouteActive(path, {})).toBe(true);
    expect(isPrimarySidebarFeatureActive("collections", path, {})).toBe(false);
  },
);
