import { expect, test, vi } from "vitest";
import { needsUnreadBlockUpgrade } from "../e2e/stages/compilation-upgrade";

function fixture(currentReviews: { id: string; status: string }[] = []) {
  const get = vi.fn(async <T>(path: string): Promise<T> => {
    if (path.endsWith("?limit=1")) return currentReviews as T;
    if (path.endsWith("/report"))
      return {
        findings: [
          {
            direction: "source_to_draft",
            sources: [{ text: "", kind: "figure", requires_review: true }],
          },
        ],
      } as T;
    return { id: "review_old", status: "completed" } as T;
  });
  const publication = { run: "run_stale", document: "document_one" };
  const history = [
    { run: "run_original", document: "document_one", review: "review_old" },
  ];
  return { api: { get }, publication, history, draft: { sections: [] } };
}

test("recovers the saved intermediate draft using its original document review", async () => {
  const f = fixture();
  expect(
    await needsUnreadBlockUpgrade(f.api, "/collection", f.publication, f.draft, f.history),
  ).toBe(true);
  expect(f.api.get).toHaveBeenCalledWith(
    "/collection/compilation-runs/run_original/reviews/review_old/report",
  );
});

test.each(["running", "uncertain", "completed"])(
  "does not replace an intermediate draft with an unrecorded %s review",
  async (status) => {
    const f = fixture([{ id: "review_current", status }]);
    expect(
      await needsUnreadBlockUpgrade(f.api, "/collection", f.publication, f.draft, f.history),
    ).toBe(false);
    expect(f.api.get).toHaveBeenCalledTimes(1);
  },
);

test("does not use another document's history as repair evidence", async () => {
  const f = fixture();
  expect(
    await needsUnreadBlockUpgrade(
      f.api,
      "/collection",
      { ...f.publication, document: "document_other" },
      f.draft,
      f.history,
    ),
  ).toBe(false);
  expect(f.api.get).not.toHaveBeenCalled();
});

test("does not rebuild a draft already carrying the source limit contract", async () => {
  const f = fixture();
  expect(
    await needsUnreadBlockUpgrade(
      f.api,
      "/collection",
      f.publication,
      { ...f.draft, validation: { unread_source_blocks: "retained" } },
      f.history,
    ),
  ).toBe(false);
  expect(f.api.get).not.toHaveBeenCalled();
});
