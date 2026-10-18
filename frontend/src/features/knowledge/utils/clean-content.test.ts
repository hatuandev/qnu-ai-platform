import assert from "node:assert/strict";
import { test } from "node:test";
import type { StudioOCRPage } from "@/types/studio-ocr";
import {
  buildStudioMarkdown,
  changedLines,
  locateIssueOffset,
  mapCleanPages,
} from "./clean-content";

const pages = [2, 3].map(
  (pageNumber) =>
    ({ pageNumber, markdown: `body ${pageNumber}` }) as StudioOCRPage,
);
test("real page boundaries roundtrip; unknown pagination stays unknown", () => {
  const codePages = [{ ...pages[0], markdown: "    code  block  " }];
  assert.equal(
    mapCleanPages(buildStudioMarkdown(codePages, {}), codePages)[2],
    "    code  block  ",
  );
  const md = buildStudioMarkdown(pages, { 3: "changed" });
  assert.deepEqual(mapCleanPages(md, pages), { 2: "body 2", 3: "changed" });
  const unmapped = [pages[0]];
  assert.equal(buildStudioMarkdown(unmapped, {}, false), "body 2");
  assert.deepEqual(mapCleanPages("draft", unmapped, false), { 2: "draft" });
  assert.throws(() => mapCleanPages("draft", pages, false));
});
test("missing, reordered or duplicate pages cannot silently overwrite draft", () => {
  assert.throws(() => mapCleanPages("<!-- Trang 2 -->body", pages));
  assert.throws(() =>
    mapCleanPages("<!-- Trang 3 -->A\n<!-- Trang 2 -->B", pages),
  );
  assert.throws(() =>
    mapCleanPages("<!-- Trang 2 -->A\n<!-- Trang 2 -->B", pages),
  );
  assert.throws(() =>
    mapCleanPages("prefix\n<!-- Trang 2 -->A\n<!-- Trang 3 -->B", pages),
  );
});
test("diff keeps original and edited numbers and conditions verbatim", () => {
  assert.deepEqual(changedLines("Không 24,125", "25,13"), [
    { id: "1", before: "Không 24,125", after: "25,13" },
  ]);
});

test("issue line offsets point inside the evidenced page, never another page", () => {
  const draft = "<!-- Trang 2 -->\n\nbody\nbroken\n\n<!-- Trang 3 -->\n\nnext";
  const issue = {
    id: "issue",
    code: "width",
    severity: "warning" as const,
    message: "check",
    page_number: 2,
    line_number: 4,
  };
  assert.equal(locateIssueOffset(draft, "body\nbroken", 2, issue), 5);
  assert.equal(locateIssueOffset(draft, "next", 3, issue), null);
});
