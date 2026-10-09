/**
 * Global Fetch Interceptor for QNU AI Platform — Automatic SSO Bearer Token Injection
 *
 * Intercepts outgoing window.fetch calls targeting trusted '/platform/*' API endpoints,
 * strictly verifying origin and pathname before injecting the active QNU SSO Bearer Token.
 * Handles single-flight silent renew, zero-header internal 401 retry, and preserves original Request body/headers.
 */

import { runtimeConfig } from "../config/runtime";
import {
  getAccessToken,
  getUserManager,
  setCachedAccessToken,
} from "./oidc";

let isInterceptorInstalled = false;
let silentRenewPromise: Promise<string | null> | null = null;

export function resolveTrustedOrigins(
  config: { apiBaseUrl?: string; bffBaseUrl?: string } = runtimeConfig,
  currentOrigin: string = typeof window !== "undefined"
    ? window.location.origin
    : "http://localhost:3000",
): Set<string> {
  const trusted = new Set<string>();
  if (currentOrigin) {
    try {
      trusted.add(new URL(currentOrigin).origin);
    } catch {
      // ignore
    }
  }

  const parseAndAdd = (baseUrl?: string) => {
    if (!baseUrl) return;
    try {
      if (/^https?:\/\//i.test(baseUrl)) {
        trusted.add(new URL(baseUrl).origin);
      }
    } catch {
      // ignore
    }
  };

  parseAndAdd(config.apiBaseUrl);
  parseAndAdd(config.bffBaseUrl);

  return trusted;
}

export function isTrustedPlatformApiRequest(
  input: RequestInfo | URL,
  config: { apiBaseUrl?: string; bffBaseUrl?: string } = runtimeConfig,
  currentOrigin: string = typeof window !== "undefined"
    ? window.location.origin
    : "http://localhost:3000",
  allowedPrefix: string = "/platform",
): boolean {
  const urlString =
    typeof input === "string"
      ? input
      : input instanceof URL
        ? input.href
        : (input as Request).url;

  let parsed: URL;
  try {
    parsed = new URL(urlString, currentOrigin);
  } catch {
    return false;
  }

  // 1. Origin check: Must strictly match one of the trusted origins
  const trustedOrigins = resolveTrustedOrigins(config, currentOrigin);
  if (!trustedOrigins.has(parsed.origin)) {
    return false;
  }

  // 2. Pathname check: Must strictly belong to allowed API prefix (e.g. /platform or /platform/...)
  // Query parameters containing '/platform/' (e.g. ?next=/platform/test) have pathname '/' and will NOT match.
  const pathname = parsed.pathname;
  const normalizedPrefix = allowedPrefix.startsWith("/")
    ? allowedPrefix
    : `/${allowedPrefix}`;
  const prefixWithSlash = normalizedPrefix.endsWith("/")
    ? normalizedPrefix
    : `${normalizedPrefix}/`;

  if (pathname !== normalizedPrefix && !pathname.startsWith(prefixWithSlash)) {
    return false;
  }

  return true;
}

export function mergeRequestHeaders(
  inputHeaders?: HeadersInit,
  initHeaders?: HeadersInit,
): Headers {
  const headers = new Headers(inputHeaders);
  if (initHeaders) {
    const overrideHeaders = new Headers(initHeaders);
    overrideHeaders.forEach((value, key) => {
      headers.set(key, value);
    });
  }
  return headers;
}

export async function performSingleFlightSilentRenew(): Promise<string | null> {
  if (silentRenewPromise) {
    return silentRenewPromise;
  }
  silentRenewPromise = (async () => {
    try {
      const mgr = getUserManager();
      const renewedUser = await mgr.signinSilent();
      if (renewedUser?.access_token) {
        setCachedAccessToken(renewedUser.access_token);
        return renewedUser.access_token;
      }
      return null;
    } catch {
      return null;
    } finally {
      silentRenewPromise = null;
    }
  })();
  return silentRenewPromise;
}

export interface AuthFetchInterceptorDeps {
  originalFetch: typeof fetch;
  getAccessToken?: () => string | null;
  setCachedAccessToken?: (token: string | null) => void;
  getUserManager?: () => {
    getUser?: () => Promise<{
      access_token?: string;
      expired?: boolean;
    } | null>;
    signinSilent?: () => Promise<{ access_token?: string } | null>;
    removeUser?: () => Promise<void>;
  };
  config?: { apiBaseUrl?: string; bffBaseUrl?: string };
  getLocation?: () => { origin: string; pathname: string; href?: string };
  onRedirectToSignIn?: () => void;
}

export function createAuthFetchInterceptor(
  deps: AuthFetchInterceptorDeps,
): (input: RequestInfo | URL, init?: RequestInit) => Promise<Response> {
  const {
    originalFetch,
    getAccessToken: getToken = getAccessToken,
    setCachedAccessToken: setToken = setCachedAccessToken,
    getUserManager: getMgr = getUserManager,
    config = runtimeConfig,
    getLocation = () =>
      typeof window !== "undefined"
        ? window.location
        : { origin: "http://localhost:3000", pathname: "/" },
    onRedirectToSignIn = () => {
      if (
        typeof window !== "undefined" &&
        window.location.pathname !== "/sign-in"
      ) {
        window.location.href = "/sign-in";
      }
    },
  } = deps;

  let silentRenewPromise: Promise<string | null> | null = null;

  const performSingleFlightRenew = async (): Promise<string | null> => {
    if (silentRenewPromise) {
      return silentRenewPromise;
    }
    silentRenewPromise = (async () => {
      try {
        const mgr = getMgr();
        const renewed = await mgr?.signinSilent?.();
        if (renewed?.access_token) {
          setToken(renewed.access_token);
          return renewed.access_token;
        }
        return null;
      } catch {
        return null;
      } finally {
        silentRenewPromise = null;
      }
    })();
    return silentRenewPromise;
  };

  return async (
    input: RequestInfo | URL,
    init?: RequestInit,
  ): Promise<Response> => {
    const loc = getLocation();
    const currentOrigin = loc.origin || "http://localhost:3000";

    // Only intercept requests strictly targeting trusted API origin and allowed prefix
    if (!isTrustedPlatformApiRequest(input, config, currentOrigin)) {
      return originalFetch(input, init);
    }

    // Merge headers: preserve caller headers from input Request and init
    const inputHeaders = input instanceof Request ? input.headers : undefined;
    const headers = mergeRequestHeaders(inputHeaders, init?.headers);

    const callerProvidedAuth =
      headers.has("Authorization") || headers.has("authorization");

    let token = getToken();
    if (!token && !callerProvidedAuth) {
      try {
        const mgr = getMgr();
        const user = await mgr?.getUser?.();
        if (user?.access_token && !user.expired) {
          token = user.access_token;
          setToken(token);
        }
      } catch {
        // ignore
      }
    }

    if (!callerProvidedAuth && token) {
      headers.set("Authorization", `Bearer ${token}`);
    }

    const credentials =
      init?.credentials ??
      (input instanceof Request ? input.credentials : undefined) ??
      "include";

    // Prepare body buffering if input is a Request with body, allowing replay on 401 retry
    let bufferedBody: BodyInit | null | undefined = init?.body;
    if (
      input instanceof Request &&
      !init?.body &&
      input.body &&
      !["GET", "HEAD"].includes((input.method || "").toUpperCase())
    ) {
      try {
        const cloned = input.clone();
        bufferedBody = await cloned.arrayBuffer();
      } catch {
        // ignore
      }
    }

    const buildRequestInit = (currentHeaders: Headers): RequestInit => ({
      ...init,
      headers: currentHeaders,
      credentials,
      body: bufferedBody !== undefined ? bufferedBody : init?.body,
    });

    const executeFetch = async (currentHeaders: Headers): Promise<Response> => {
      const modifiedInit = buildRequestInit(currentHeaders);
      if (input instanceof Request) {
        return originalFetch(new Request(input, modifiedInit));
      }
      return originalFetch(input, modifiedInit);
    };

    // First attempt
    let response = await executeFetch(headers);

    // Handle 401: single-flight silent renew, retry exactly once via internal loop, no custom server headers
    if (response.status === 401 && !callerProvidedAuth) {
      const renewedToken = await performSingleFlightRenew();
      if (renewedToken) {
        headers.set("Authorization", `Bearer ${renewedToken}`);
        response = await executeFetch(headers);
        return response;
      }

      // Renew failed: clean session, redirect to sign-in
      setToken(null);
      try {
        const mgr = getMgr();
        await mgr?.removeUser?.();
      } catch {
        // ignore
      }
      onRedirectToSignIn();
    }

    return response;
  };
}

export function installAuthFetchInterceptor(
  deps?: Partial<AuthFetchInterceptorDeps>,
): void {
  if (isInterceptorInstalled || typeof window === "undefined") {
    return;
  }
  isInterceptorInstalled = true;

  const originalFetch = deps?.originalFetch || window.fetch.bind(window);
  window.fetch = createAuthFetchInterceptor({
    originalFetch,
    getAccessToken: deps?.getAccessToken,
    setCachedAccessToken: deps?.setCachedAccessToken,
    getUserManager: deps?.getUserManager,
    config: deps?.config,
    getLocation: deps?.getLocation,
    onRedirectToSignIn: deps?.onRedirectToSignIn,
  });
}
