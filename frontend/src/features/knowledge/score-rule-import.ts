import { z } from "zod";

const object = z.record(z.string(), z.unknown());

/** Import definitions, never trust approval stamps contained in an exported file. */
export function parseRuleImport(raw: string): Record<string, unknown>[] {
  const parsed: unknown = JSON.parse(raw);
  const entries = Array.isArray(parsed) ? parsed : [parsed];
  return z
    .array(object)
    .min(1)
    .max(25)
    .parse(entries)
    .map((entry) => {
      const definition = object.parse(entry.definition ?? entry);
      const {
        status: _status,
        reviewed_by: _reviewer,
        reviewed_at: _reviewTime,
        ...draft
      } = definition;
      return draft;
    });
}
