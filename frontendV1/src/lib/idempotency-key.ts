/**
 * Idempotency keys for v1 mutations.
 *
 * The backend accepts `^[A-Za-z0-9_.:-]+$` with 1–128 characters.
 */
export function createIdempotencyKey(): string {
  if (
    typeof crypto !== "undefined" &&
    typeof crypto.randomUUID === "function"
  ) {
    return crypto.randomUUID();
  }
  return `key_${Date.now()}_${Math.random().toString(36).slice(2, 12)}`;
}
