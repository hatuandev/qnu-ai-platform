import { useEffect, useRef } from "react";
import { getTokenState } from "@/app/api/v1/session-token";

/** Mounted intent only; an older account must never install a preview/result. */
export function useActionScope() {
  const session = useRef(getTokenState().sessionId).current;
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  return () => mounted.current && getTokenState().sessionId === session;
}
