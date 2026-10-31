export function progressWaitMs(
  total: number,
  concurrency: number,
  perPartMs: number,
  queueMs = 0,
  minMs = 240_000,
): number {
  const parts = Math.max(1, total);
  const slots = Math.max(1, Math.min(parts, concurrency));
  // Round the number of waves, not the product of duration and part count.
  return Math.max(
    minMs,
    Math.ceil(parts / slots) * (perPartMs + queueMs) + 60_000,
  );
}
