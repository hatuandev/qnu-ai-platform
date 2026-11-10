/**
 * Spelling suggestion sequential replacement helpers.
 *
 * Guarantees that multiple suggestions applied to the same text unit
 * are executed from right-to-left (descending character offsets)
 * so preceding character positions remain strictly invariant.
 */

import type { Suggestion, TextChange, TextUnit } from "@/api/ocr/requests";

export type SuggestionDecision =
  | { status: "pending" }
  | { status: "applied" }
  | { status: "ignored" }
  | { status: "custom"; customReplacement: string };

export interface AppliedResult {
  resultText: string;
  appliedCount: number;
  errors: string[];
}

export function splitTextAtSuggestion(
  text: string,
  start: number,
  end: number,
) {
  const chars = Array.from(text);
  return {
    before: chars.slice(0, start).join(""),
    original: chars.slice(start, end).join(""),
    after: chars.slice(end).join(""),
  };
}

/**
 * Apply multiple text replacements on a single original string from right to left.
 */
export function applySuggestionsToText(
  originalText: string,
  replacements: Array<{
    start: number;
    end: number;
    original: string;
    replacement: string;
  }>,
): AppliedResult {
  const errors: string[] = [];
  let chars = Array.from(originalText);
  let appliedCount = 0;

  // Sort descending by start offset to prevent character drift
  const sorted = [...replacements].sort((a, b) => b.start - a.start);

  for (const rep of sorted) {
    if (rep.start < 0 || rep.end > chars.length || rep.start >= rep.end) {
      errors.push(
        `Vị trí [${rep.start}, ${rep.end}] vượt ngoài độ dài chuỗi (${chars.length}).`,
      );
      continue;
    }

    const actualOriginal = chars.slice(rep.start, rep.end).join("");
    if (actualOriginal !== rep.original) {
      errors.push(
        `Nguyên văn không khớp tại [${rep.start}, ${rep.end}]: mong đợi "${rep.original}", thực tế "${actualOriginal}".`,
      );
      continue;
    }

    chars = [
      ...chars.slice(0, rep.start),
      ...rep.replacement,
      ...chars.slice(rep.end),
    ];
    appliedCount++;
  }

  return {
    resultText: chars.join(""),
    appliedCount,
    errors,
  };
}

/**
 * Builds durable TextChange array from text units and user review decisions.
 */
export function buildTextChanges(
  units: TextUnit[],
  suggestions: Suggestion[],
  decisions: Map<string, SuggestionDecision>,
): {
  changes: TextChange[];
  totalApplied: number;
  errors: string[];
} {
  const unitMap = new Map(units.map((u) => [u.evidence_id, u]));
  const suggestionsByEvidence = new Map<
    string,
    Array<{
      start: number;
      end: number;
      original: string;
      replacement: string;
    }>
  >();

  let totalApplied = 0;
  const allErrors: string[] = [];

  // Group approved/custom suggestions by evidence_id
  for (const s of suggestions) {
    const key = `${s.evidence_id}:${s.start}:${s.end}`;
    const decision = decisions.get(key);

    if (!decision) continue;

    let targetReplacement: string | null = null;
    if (decision.status === "applied") {
      targetReplacement = s.replacement;
    } else if (decision.status === "custom") {
      targetReplacement = decision.customReplacement;
    }

    if (targetReplacement !== null) {
      const list = suggestionsByEvidence.get(s.evidence_id) || [];
      list.push({
        start: s.start,
        end: s.end,
        original: s.original,
        replacement: targetReplacement,
      });
      suggestionsByEvidence.set(s.evidence_id, list);
    }
  }

  const changes: TextChange[] = [];

  for (const [evidenceId, repList] of suggestionsByEvidence.entries()) {
    const unit = unitMap.get(evidenceId);
    if (!unit) {
      allErrors.push(`Không tìm thấy đơn vị văn bản [${evidenceId}].`);
      continue;
    }

    const { resultText, appliedCount, errors } = applySuggestionsToText(
      unit.text,
      repList,
    );

    totalApplied += appliedCount;
    allErrors.push(...errors);

    if (resultText !== unit.text) {
      changes.push({
        evidence_id: evidenceId,
        before: unit.text,
        after: resultText,
      });
    }
  }

  return {
    changes,
    totalApplied,
    errors: allErrors,
  };
}
