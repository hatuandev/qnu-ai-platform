import { isSsoEnabled } from "@/api/sso";
import { DevSessionGate } from "@/components/dev/dev-session-gate";
import { SsoSessionGate } from "./sso-session-gate";

/**
 * Picks the sign-in mechanism once per load: QNU SSO when it is configured
 * (always in production builds unless explicitly disabled), the local dev
 * bridge otherwise.
 */
export function AdminSessionGate({ children }: { children: React.ReactNode }) {
  if (isSsoEnabled()) {
    return <SsoSessionGate>{children}</SsoSessionGate>;
  }
  return <DevSessionGate>{children}</DevSessionGate>;
}
