import { afterEach, describe, expect, test, vi } from "vitest";

import { syntheticRankings } from "../fixtures/rankings";
import type { RankingsSearchResponse } from "../types/rankings";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  vi.resetModules();
});

describe("ranking API client", () => {
  test("requests the search endpoint with the term and returns response items", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://localhost:8000/");
    const payload: RankingsSearchResponse = {
      items: syntheticRankings.slice(0, 2),
      total: 2,
      limit: 50,
      offset: 0,
    };
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const { fetchRankings } = await import("./rankings");
    const result = await fetchRankings({ term: "202701" });

    expect(result).toEqual(payload.items);
    expect(fetchMock).toHaveBeenCalledOnce();
    const requestUrl = new URL(String(fetchMock.mock.calls[0]?.[0]));
    expect(requestUrl.pathname).toBe("/api/v1/rankings/search");
    expect(requestUrl.searchParams.get("term")).toBe("202701");
  });

  test("throws for a non-successful API response", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://localhost:8000");
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 503 })),
    );

    const { fetchRankings } = await import("./rankings");

    await expect(fetchRankings({ term: "202701" })).rejects.toThrow(
      "Ranking request failed with status 503.",
    );
  });

  test("uses synthetic fixtures without requesting the API when no base URL is set", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "");
    const fetchMock = vi.fn<typeof fetch>();
    vi.stubGlobal("fetch", fetchMock);

    const { fetchRankings, isUsingMockData } = await import("./rankings");
    const result = await fetchRankings({ term: "202701" });

    expect(isUsingMockData).toBe(true);
    expect(result).toEqual(
      syntheticRankings.filter((ranking) => ranking.term === "202701"),
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
