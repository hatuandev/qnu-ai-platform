/**
 * In-memory v1 session token.
 *
 * The token is deliberately *not* persisted: no localStorage/sessionStorage, so a
 * reload or a new tab starts unauthenticated and the UI asks for a dev access key
 * again. Nothing here writes to disk or to the URL.
 */

export type V1TokenState = {
  token: string | null;
  /** True when the backend answered 401, so the UI can explain why. */
  expired: boolean;
  /**
   * Monotonic session counter. Query keys use it instead of the token so a
   * credential never ends up in devtools, logs or a cache key.
   */
  sessionId: number;
};

let state: V1TokenState = { token: null, expired: false, sessionId: 0 };
const listeners = new Set<() => void>();

function emit(): void {
  for (const listener of listeners) listener();
}

export function getTokenState(): V1TokenState {
  return state;
}

export function getAccessToken(): string | null {
  return state.token;
}

export function setAccessToken(token: string): void {
  state = { token, expired: false, sessionId: state.sessionId + 1 };
  emit();
}

export function clearAccessToken(options?: {
  sessionId?: number;
  expired?: boolean;
}): boolean {
  if (
    options?.sessionId !== undefined &&
    options.sessionId !== state.sessionId
  ) {
    return false;
  }
  const expired = options?.expired ?? false;
  if (state.token === null && state.expired === expired) return false;
  state = { token: null, expired, sessionId: state.sessionId + 1 };
  emit();
  return true;
}

export function subscribeToken(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
