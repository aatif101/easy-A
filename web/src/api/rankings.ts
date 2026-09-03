import { syntheticRankings } from "../fixtures/rankings";
import type { RankingLoader, RankingsSearchResponse } from "../types/rankings";

const trimTrailingSlash = (value: string): string => value.replace(/\/+$/, "");

export const apiBaseUrl = trimTrailingSlash(import.meta.env.VITE_API_BASE_URL?.trim() ?? "");
export const isUsingMockData = apiBaseUrl.length === 0;

export const fetchRankings: RankingLoader = async ({ term }, signal) => {
  if (isUsingMockData) {
    return syntheticRankings.filter((ranking) => ranking.term === term);
  }

  const url = new URL(`${apiBaseUrl}/api/v1/rankings/search`);
  url.searchParams.set("term", term);
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) {
    throw new Error(`Ranking request failed with status ${response.status}.`);
  }
  const searchResponse = (await response.json()) as RankingsSearchResponse;
  return searchResponse.items;
};
