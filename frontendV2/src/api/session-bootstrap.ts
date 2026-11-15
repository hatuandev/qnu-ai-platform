/**
 * One-shot handoff from the SSO callback page to the session gate.
 *
 * The callback already fetched the actor and workspaces to verify the login;
 * the gate reuses that snapshot so the dashboard draws without a second
 * "Đang kiểm tra phiên đăng nhập…" stop. The snapshot is bound to the current
 * access token and expires quickly, so it can never outlive the session.
 */

import type { AuthActor } from "@/api/auth/types";
import type { Workspace } from "@/api/workspaces/types";
import { getAccessToken } from "./session-token";

const MAX_AGE_MS = 30_000;

type Snapshot = {
  token: string;
  actor: AuthActor;
  workspaces: Workspace[];
  createdAt: number;
};

let snapshot: Snapshot | null = null;

export function primeSessionBootstrap(
  actor: AuthActor,
  workspaces: Workspace[],
): void {
  const token = getAccessToken();
  if (!token) {
    snapshot = null;
    return;
  }
  snapshot = { token, actor, workspaces, createdAt: Date.now() };
}

export function peekSessionBootstrap(): {
  actor: AuthActor;
  workspaces: Workspace[];
} | null {
  if (!snapshot) return null;
  const isFresh = Date.now() - snapshot.createdAt <= MAX_AGE_MS;
  if (!isFresh || snapshot.token !== getAccessToken()) {
    snapshot = null;
    return null;
  }
  return { actor: snapshot.actor, workspaces: snapshot.workspaces };
}

export function clearSessionBootstrap(): void {
  snapshot = null;
}
