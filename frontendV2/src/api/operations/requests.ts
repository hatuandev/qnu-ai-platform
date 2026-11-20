import { v1Client } from "../v1-client";
import { operationsPaths } from "./endpoints";
import type { SystemResetRequest, SystemResetResponse } from "./types";

export async function systemResetAndSeed(
  payload: SystemResetRequest,
): Promise<SystemResetResponse> {
  return v1Client.post<SystemResetResponse>(
    operationsPaths.systemResetAndSeed(),
    payload,
    { timeoutMs: 120_000 },
  );
}
