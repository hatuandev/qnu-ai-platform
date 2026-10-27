/**
 * Shared search-param contract for the v1 list screens.
 *
 * The URL is the only source of paging state, so a deep link or an F5 restores
 * the same page without any client cache. The backend has no `total_pages`
 * field, so nothing here assumes one.
 */

import { z } from "zod";

export const PAGE_SIZE_OPTIONS = [10, 20, 50, 100] as const;
export const DEFAULT_PAGE_SIZE = 20;

export const pageSearchSchema = z.object({
  page: z.coerce.number().int().min(1).catch(1),
  pageSize: z.coerce
    .number()
    .int()
    .refine((value) => (PAGE_SIZE_OPTIONS as readonly number[]).includes(value))
    .catch(DEFAULT_PAGE_SIZE),
});

export type PageSearch = z.infer<typeof pageSearchSchema>;

/** Default search object for links that must declare paging explicitly. */
export const DEFAULT_PAGE_SEARCH: PageSearch = {
  page: 1,
  pageSize: DEFAULT_PAGE_SIZE,
};
