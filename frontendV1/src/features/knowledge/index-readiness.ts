import type { IndexReadiness, IndexRun } from "./index-types";
import type { PublishedResponse } from "./publication-types";

export function matchesPublishedIndex(
  readiness: IndexReadiness | undefined,
  published: PublishedResponse | null | undefined,
  active: IndexRun | undefined,
): boolean {
  return Boolean(
    readiness?.status === "ready" &&
      published &&
      active?.is_active &&
      active.status === "completed" &&
      readiness.index_run_id === active.id &&
      readiness.version_id === published.version.id &&
      readiness.version_state === published.version.state_version &&
      readiness.bundle_sha256 === published.version.bundle_sha256 &&
      readiness.publication_decision_id === published.decision.id,
  );
}
