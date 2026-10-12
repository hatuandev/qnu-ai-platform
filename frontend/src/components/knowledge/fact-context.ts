export function getFactContext(raw: Record<string, unknown>) {
  const temporal = raw.temporal_context;
  const qualifiers = raw.qualifiers;
  const year =
    temporal && typeof temporal === "object" && "year" in temporal
      ? temporal.year
      : raw.year;
  const method =
    qualifiers && typeof qualifiers === "object" && "method" in qualifiers
      ? qualifiers.method
      : null;
  return {
    year:
      typeof year === "number" || typeof year === "string"
        ? String(year)
        : "Chưa rõ",
    method: typeof method === "string" && method ? method : "Không ghi riêng",
  };
}
