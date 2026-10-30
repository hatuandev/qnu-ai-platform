/** One recovery on an explicitly rerun stage; never replay an uncertain call. */
export function canRecoverAdmissionCompilation(
  run: { status: string; error_code?: string; provider_id?: string | null },
  publication: { compilationRecoveryOf?: string; review?: string; version?: string },
  providerId: string | undefined,
  outputLimit: number | null | undefined,
): outputLimit is number {
  return (
    run.status === "failed" &&
    run.error_code === "chat_output_truncated" &&
    !!providerId && run.provider_id === providerId &&
    !publication.compilationRecoveryOf && !publication.review && !publication.version &&
    typeof outputLimit === "number" && Number.isSafeInteger(outputLimit) &&
    outputLimit >= 8192
  );
}
