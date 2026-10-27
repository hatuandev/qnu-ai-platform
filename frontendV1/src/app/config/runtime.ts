type RuntimeOverrides = {
  apiBaseUrl?: string;
  bffBaseUrl?: string;
  authMode?: "bff" | "demo";
};

declare global {
  interface Window {
    __QNU_KTX_CONFIG__?: RuntimeOverrides;
  }
}

function normalizeBasePath(
  value: string | undefined,
  fallback: string,
): string {
  const candidate = value?.trim() || fallback;
  if (/^https?:\/\//i.test(candidate)) return candidate.replace(/\/$/, "");

  const withLeadingSlash = candidate.startsWith("/")
    ? candidate
    : `/${candidate}`;
  return withLeadingSlash.replace(/\/+$/, "") || "/";
}

const injectedConfig =
  typeof window === "undefined" ? undefined : window.__QNU_KTX_CONFIG__;

export const runtimeConfig = Object.freeze({
  apiBaseUrl: normalizeBasePath(
    injectedConfig?.apiBaseUrl ?? import.meta.env.VITE_API_BASE_URL,
    "/api",
  ),
  bffBaseUrl: normalizeBasePath(
    injectedConfig?.bffBaseUrl ?? import.meta.env.VITE_BFF_BASE_URL,
    "/bff",
  ),
  // Standalone reference only. This is not a verified backend identity.
  authMode: "demo" as const,
  templateMode: true,
});

export type RuntimeConfig = typeof runtimeConfig;
