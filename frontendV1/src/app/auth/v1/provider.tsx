import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";
import {
  ApiProblemError,
  authPaths,
  clearAccessToken,
  getTokenState,
  setAccessToken,
  subscribeToken,
  v1Client,
  v1PublicClient,
} from "@/app/api/v1";
import {
  clearDevAutoLoginSuppression,
  isDevAutoLoginAvailable,
  isDevAutoLoginSuppressed,
  isSsoCallbackActive,
  requestDevAutoLogin,
  subscribeSsoCallback,
  suppressDevAutoLogin,
} from "@/app/auth/v1/dev-auto-login";
import { loginWithSso, logoutSso } from "@/app/auth/v1/oidc";
import type {
  V1Actor,
  V1ActorResponse,
  V1LoginResponse,
} from "@/app/auth/v1/types";

export type V1AuthStatus =
  | "anonymous"
  | "verifying"
  | "authenticated"
  | "error";

/** Local auto-login lifecycle; only meaningful while `status === "anonymous"`. */
export type V1AutoLoginPhase = "idle" | "pending" | "succeeded" | "failed";

export type V1AuthContextValue = {
  actor: V1Actor | null;
  status: V1AuthStatus;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: Error | null;
  sessionId: number;
  /** A previous token was rejected by the backend with 401. */
  expired: boolean;
  /** True only in the Vite dev server build, never in preview or production. */
  autoLoginAvailable: boolean;
  autoLoginPhase: V1AutoLoginPhase;
  autoLoginError: Error | null;
  signIn: (accessKey: string) => Promise<void>;
  signInWithSso: (returnUrl?: string) => Promise<void>;
  signOut: () => Promise<void>;
  refetch: () => void;
  /** Clears the logout suppression and asks the dev bridge for a token again. */
  retryAutoLogin: () => void;
};

const V1AuthContext = createContext<V1AuthContextValue | null>(null);

export const v1MeQueryKey = (sessionId: number) =>
  ["v1", sessionId, "auth", "me"] as const;

export function isValidActor(data: unknown): data is V1Actor {
  if (!data || typeof data !== "object") return false;
  const a = data as Partial<V1Actor>;
  return (
    typeof a.actor_id === "string" &&
    a.actor_id.trim().length > 0 &&
    typeof a.username === "string" &&
    a.username.trim().length > 0 &&
    a.authenticated === true &&
    Array.isArray(a.permissions) &&
    Array.isArray(a.roles)
  );
}

/**
 * A local auto-login attempt is only allowed to install its token while *every*
 * condition below still holds. Checking only "am I still mounted" or "was
 * suppression set before the request" is not enough: an SSO callback, a manual
 * key login, a logout or a newer attempt can all land while the bridge is in
 * flight, and the late response must then be dropped instead of winning.
 */
type AutoLoginTicket = {
  /** Bumped by every deliberate auth transition (sign-in, SSO, sign-out). */
  epoch: number;
  /** Token-store generation observed when the request started. */
  sessionAtStart: number;
  /** Identifies this attempt; a newer attempt invalidates this one. */
  attempt: number;
};

export function V1AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const tokenState = useSyncExternalStore(
    subscribeToken,
    getTokenState,
    getTokenState,
  );
  const ssoCallbackActive = useSyncExternalStore(
    subscribeSsoCallback,
    isSsoCallbackActive,
    () => false,
  );

  const autoLoginAvailable = isDevAutoLoginAvailable();
  const [autoLoginPhase, setAutoLoginPhase] =
    useState<V1AutoLoginPhase>("idle");
  const [autoLoginError, setAutoLoginError] = useState<Error | null>(null);

  // One attempt per page session: StrictMode's double mount must not log in
  // twice, and a rejected token must not start a retry loop.
  const autoLoginStartedRef = useRef(false);
  // Invalidates every in-flight auto-login response.
  const authEpochRef = useRef(0);
  const autoLoginAttemptRef = useRef(0);
  // Deliberately not reset on StrictMode's remount: the provider instance is the
  // same, and the shared single-flight promise must stay usable.
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      // A late response is dropped while this stays false. The epoch is
      // deliberately *not* bumped here: StrictMode runs mount → cleanup →
      // mount on the same instance, and bumping it would invalidate the single
      // request the first mount already started.
      mountedRef.current = false;
    };
  }, []);

  // Invalidate synchronously when SSO takes over, including when the callback
  // starts and finishes before a pending bridge response arrives.
  useEffect(
    () =>
      subscribeSsoCallback(() => {
        if (!isSsoCallbackActive()) return;
        authEpochRef.current += 1;
        if (mountedRef.current) {
          setAutoLoginPhase("idle");
          setAutoLoginError(null);
        }
      }),
    [],
  );

  const meQuery = useQuery({
    queryKey: v1MeQueryKey(tokenState.sessionId),
    queryFn: ({ signal }) =>
      v1Client.get<V1ActorResponse>(authPaths.me, { signal }),
    enabled: Boolean(tokenState.token),
    retry: false,
    refetchOnWindowFocus: false,
    staleTime: 60_000,
  });

  const isAutoLoginResultCurrent = useCallback(
    (ticket: AutoLoginTicket): boolean => {
      if (!mountedRef.current) return false;
      if (ticket.epoch !== authEpochRef.current) return false;
      if (ticket.attempt !== autoLoginAttemptRef.current) return false;
      // An explicit logout during the request always wins.
      if (isDevAutoLoginSuppressed()) return false;
      if (isSsoCallbackActive()) return false;
      const current = getTokenState();
      // Another flow (SSO callback, manual key, logout) already wrote the store.
      if (current.sessionId !== ticket.sessionAtStart) return false;
      // A session exists; never replace it with a dev token.
      return current.token === null;
    },
    [],
  );

  const runAutoLogin = useCallback(() => {
    if (isSsoCallbackActive()) return;
    const ticket: AutoLoginTicket = {
      epoch: authEpochRef.current,
      sessionAtStart: getTokenState().sessionId,
      attempt: autoLoginAttemptRef.current + 1,
    };
    autoLoginAttemptRef.current = ticket.attempt;
    setAutoLoginError(null);
    setAutoLoginPhase("pending");

    requestDevAutoLogin()
      .then((token) => {
        if (!isAutoLoginResultCurrent(ticket)) return;
        setAccessToken(token);
        setAutoLoginPhase("succeeded");
      })
      .catch((cause: unknown) => {
        if (!isAutoLoginResultCurrent(ticket)) return;
        setAutoLoginError(
          cause instanceof Error
            ? cause
            : new Error("Không tự đăng nhập được bằng cấu hình local."),
        );
        setAutoLoginPhase("failed");
      });
  }, [isAutoLoginResultCurrent]);

  const rawActor = tokenState.token ? meQuery.data?.actor : null;
  const actor = isValidActor(rawActor) ? rawActor : null;
  const actorInvalid = Boolean(tokenState.token && meQuery.data && !actor);

  const status: V1AuthStatus = useMemo(() => {
    if (!tokenState.token) return "anonymous";
    if (meQuery.isError || actorInvalid) return "error";
    if (actor) return "authenticated";
    return "verifying";
  }, [actor, actorInvalid, meQuery.isError, tokenState.token]);

  useEffect(() => {
    if (autoLoginStartedRef.current) return;
    if (!autoLoginAvailable) return;
    // Never replace a session that already exists (SSO callback, manual key).
    if (tokenState.token) return;
    if (status !== "anonymous") return;
    // An explicit logout wins until the user asks to sign in again.
    if (isDevAutoLoginSuppressed()) return;
    // The SSO callback owns the token exchange while it is on screen.
    if (ssoCallbackActive) return;
    autoLoginStartedRef.current = true;
    runAutoLogin();
  }, [
    autoLoginAvailable,
    runAutoLogin,
    ssoCallbackActive,
    status,
    tokenState.token,
  ]);

  // The bridge issued a token but `/auth/me` rejected it: explain it instead of
  // looping back into auto-login.
  useEffect(() => {
    if (!mountedRef.current) return;
    if (!tokenState.expired || autoLoginPhase !== "succeeded") return;
    setAutoLoginError(
      new Error(
        "BackendV1 từ chối token do cầu nối local cấp. Kiểm tra SECRET_KEY (tối thiểu 32 byte) và DEV_AUTH_ENABLED của backendV1.",
      ),
    );
    setAutoLoginPhase("failed");
  }, [autoLoginPhase, tokenState.expired]);

  const signIn = useCallback(
    async (accessKey: string) => {
      const response = await v1PublicClient.post<V1LoginResponse>(
        authPaths.login,
        { access_key: accessKey },
      );
      if (!response?.access_token) {
        throw new ApiProblemError({
          status: 502,
          code: "invalid_login_response",
          message: "Phản hồi đăng nhập không có access_token.",
        });
      }
      // A manual sign-in outranks any auto-login that is still in flight.
      authEpochRef.current += 1;
      queryClient.cancelQueries({ queryKey: ["v1"] });
      queryClient.removeQueries({ queryKey: ["v1"] });
      queryClient.getMutationCache().clear();
      setAccessToken(response.access_token);
    },
    [queryClient],
  );

  const signInWithSso = useCallback(async (returnUrl?: string) => {
    // The SSO redirect takes over the session; drop any pending dev login.
    authEpochRef.current += 1;
    await loginWithSso(returnUrl);
  }, []);

  const signOut = useCallback(async () => {
    // Stop the local bridge from signing the user straight back in.
    suppressDevAutoLogin();
    authEpochRef.current += 1;
    autoLoginStartedRef.current = true;
    if (mountedRef.current) {
      setAutoLoginError(null);
      setAutoLoginPhase("idle");
    }
    try {
      await v1Client.post(authPaths.logout);
    } catch {
      // A failed logout must still clear local state.
    }
    clearAccessToken();
    queryClient.cancelQueries({ queryKey: ["v1"] });
    queryClient.removeQueries({ queryKey: ["v1"] });
    queryClient.getMutationCache().clear();
    await logoutSso();
  }, [queryClient]);

  const retryAutoLogin = useCallback(() => {
    if (isSsoCallbackActive()) return;
    clearDevAutoLoginSuppression();
    autoLoginStartedRef.current = true;
    runAutoLogin();
  }, [runAutoLogin]);

  const authError = useMemo(() => {
    if (actorInvalid) {
      return new Error(
        "Danh tính người dùng trả về từ /auth/me không hợp lệ hoặc chưa xác thực.",
      );
    }
    return meQuery.error instanceof Error ? meQuery.error : null;
  }, [actorInvalid, meQuery.error]);

  const value = useMemo<V1AuthContextValue>(
    () => ({
      actor,
      status,
      isAuthenticated: status === "authenticated",
      isLoading: status === "verifying",
      error: authError,
      sessionId: tokenState.sessionId,
      expired: tokenState.expired,
      autoLoginAvailable,
      autoLoginPhase,
      autoLoginError,
      signIn,
      signInWithSso,
      signOut,
      refetch: () => void meQuery.refetch(),
      retryAutoLogin,
    }),
    [
      actor,
      authError,
      autoLoginAvailable,
      autoLoginError,
      autoLoginPhase,
      meQuery.refetch,
      retryAutoLogin,
      signIn,
      signInWithSso,
      signOut,
      status,
      tokenState.expired,
      tokenState.sessionId,
    ],
  );

  return (
    <V1AuthContext.Provider value={value}>{children}</V1AuthContext.Provider>
  );
}

export function useV1Auth(): V1AuthContextValue {
  const value = useContext(V1AuthContext);
  if (!value) throw new Error("useV1Auth must be used within V1AuthProvider");
  return value;
}
