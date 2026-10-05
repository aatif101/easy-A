import type { RankingLoader, RankingQuery, SectionRanking } from "../types/rankings";

const PAGE = 200;
const MAX_SECTIONS = 1000;

/**
 * Loads every section matching each filter (one request per page, the API caps pages at 200)
 * and merges them by CRN. Sorting by A% needs the whole set, not a server-ranked first page.
 */
export const loadAllSections = async (
  loader: RankingLoader,
  filters: Omit<RankingQuery, "limit" | "offset">[],
  signal?: AbortSignal,
): Promise<SectionRanking[]> => {
  const byCrn = new Map<string, SectionRanking>();
  await Promise.all(
    filters.map(async (filter) => {
      for (let offset = 0; offset < MAX_SECTIONS; offset += PAGE) {
        const page = await loader({ ...filter, limit: PAGE, offset }, signal);
        for (const item of page.items) byCrn.set(item.crn, item);
        if (page.items.length < PAGE || offset + PAGE >= page.total) break;
      }
    }),
  );
  return [...byCrn.values()];
};
