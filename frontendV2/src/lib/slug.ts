/**
 * Converts text (including Vietnamese diacritics) to a URL-safe slug.
 * Compatible with backend workspace code validation: `^[a-z0-9]+(?:[-_][a-z0-9]+)*$`.
 */
export function slugify(str: string): string {
  return str
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[đĐ]/g, "d")
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, "-")
    .replace(/[-_]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 64);
}
