import { useQuery } from "@tanstack/react-query";
import { useLocation, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo } from "react";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import { useWorkspaceQuery } from "@/features/workspaces/queries";
import {
  internalWorkspacePath,
  parseWorkspaceLink,
  publicWorkspacePath,
} from "@/navigation/workspace-links";

declare module "@tanstack/history" {
  interface HistoryState {
    workspacePath?: string;
  }
}

export function WorkspaceLinkBridge() {
  const location = useLocation();
  const navigate = useNavigate();
  const { sessionId } = useV1Auth();
  const link = useMemo(
    () => parseWorkspaceLink(location.pathname),
    [location.pathname],
  );
  const query = useQuery({
    queryKey: ["v1", sessionId, "workspace-link", link?.code, link?.sourceId],
    queryFn: ({ signal }) =>
      v1Client.get<{
        workspace_id: string;
        code: string;
        collection_id: string | null;
      }>("/workspaces/resolve-route", {
        searchParams: { code: link?.code, source_id: link?.sourceId },
        signal,
      }),
    enabled: Boolean(link),
    retry: false,
  });
  useEffect(() => {
    if (!link || !query.data) return;
    void navigate({
      to: internalWorkspacePath(link, query.data) as "/",
      search: true,
      hash: location.hash,
      replace: true,
      mask: {
        to: location.pathname as "/",
        search: true,
        hash: location.hash,
        unmaskOnReload: true,
      },
    });
  }, [link, query.data, location.hash, location.pathname, navigate]);
  if (!link) return <p>Không tìm thấy trang.</p>;
  if (query.isError) return <p role="alert">{query.error.message}</p>;
  return <p role="status">Đang mở workspace…</p>;
}

/** Keep existing typed resource routes while exposing compact, reloadable links. */
export function WorkspaceCanonicalLink() {
  const location = useLocation();
  const navigate = useNavigate();
  const workspaceId =
    /^\/workspaces\/(?!choose\/)([^/]+)/.exec(location.pathname)?.[1] ?? "";
  const workspace = useWorkspaceQuery(workspaceId);
  const code = workspace.data?.code;
  const path = code ? publicWorkspacePath(location.pathname, code) : undefined;
  useEffect(() => {
    if (!path || location.maskedLocation?.pathname === path) return;
    void navigate({
      to: location.pathname as "/",
      state: (previous) => ({ ...previous, workspacePath: path }),
      search: true,
      hash: location.hash,
      replace: true,
      mask: {
        to: path as "/",
        search: true,
        hash: location.hash,
        unmaskOnReload: true,
      },
    });
  }, [
    path,
    location.pathname,
    location.hash,
    location.maskedLocation?.pathname,
    navigate,
  ]);
  return null;
}
