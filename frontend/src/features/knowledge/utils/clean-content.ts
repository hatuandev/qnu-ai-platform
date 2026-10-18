import type { ContentIntegrityIssue } from "@/types/knowledge";
import type { StudioOCRPage } from "@/types/studio-ocr";

export function locateIssueOffset(
  draft: string,
  pageText: string,
  pageNumber: number,
  issue: ContentIntegrityIssue,
): number | null {
  if (issue.line_number === null) return null;
  if (issue.page_number !== null && issue.page_number !== pageNumber)
    return null;
  const lines = draft.split("\n");
  const prefix = lines.slice(0, issue.line_number - 1).join("\n");
  const absolute = prefix.length + (issue.line_number > 1 ? 1 : 0);
  const marker = new RegExp(
    `<!--\\s*(?:Trang|Page)\\s+${pageNumber}\\s*-->`,
    "i",
  ).exec(draft);
  const pageStart = draft.indexOf(
    pageText,
    marker ? marker.index + marker[0].length : 0,
  );
  return pageStart >= 0 &&
    absolute >= pageStart &&
    absolute <= pageStart + pageText.length
    ? absolute - pageStart
    : null;
}

export function buildStudioMarkdown(
  pages: StudioOCRPage[],
  edits: Record<number, string>,
  paginationKnown = true,
): string {
  return pages
    .map(
      (p) =>
        `${paginationKnown ? `<!-- Trang ${p.pageNumber} -->\n\n` : ""}${edits[p.pageNumber] ?? p.markdown}`,
    )
    .join("\n\n");
}

export function mapCleanPages(
  markdown: string,
  pages: StudioOCRPage[],
  paginationKnown = true,
): Record<number, string> {
  if (!paginationKnown) {
    if (pages.length !== 1)
      throw new Error(
        "Không có ánh xạ trang đáng tin; không tự chia nội dung.",
      );
    return { [pages[0].pageNumber]: markdown };
  }
  const markers = [
    ...markdown.matchAll(/<!--\s*(?:Trang|Page)\s+(\d+)\s*-->/gi),
  ];
  if (
    markers.length !== pages.length ||
    markdown.slice(0, markers[0]?.index ?? 0).trim()
  )
    throw new Error("Ranh giới trang đã thay đổi; cần đối chiếu lại.");
  const result: Record<number, string> = {};
  for (const [i, marker] of markers.entries()) {
    const number = Number(marker[1]);
    if (number !== pages[i].pageNumber || number in result)
      throw new Error("Thứ tự trang không khớp nguồn.");
    result[number] = markdown
      .slice(
        (marker.index ?? 0) + marker[0].length,
        markers[i + 1]?.index ?? markdown.length,
      )
      .replace(/^\n+|\n+$/g, "");
  }
  return result;
}

export function changedLines(
  before: string,
  after: string,
): { id: string; before: string; after: string }[] {
  const a = before.split("\n"),
    b = after.split("\n");
  return Array.from({ length: Math.max(a.length, b.length) }, (_, i) => ({
    id: String(i + 1),
    before: a[i] ?? "",
    after: b[i] ?? "",
  })).filter((line) => line.before !== line.after);
}
