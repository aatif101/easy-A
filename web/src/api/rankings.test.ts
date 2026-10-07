import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { syntheticRankings } from "../fixtures/rankings";
import type { RankingQuery, RankingsSearchResponse } from "../types/rankings";

const baseQuery: RankingQuery = {
  term: "202701",
  limit: 50,
  offset: 0,
};

beforeEach(() => { vi.stubEnv("VITE_USE_MOCK_DATA", "false"); });

describe("expanded search API client", () => {
  test("sends the original query, bounded pagination and cancellation to discovery", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://localhost:8000");
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const { fetchDiscovery } = await import("./rankings");
    const signal = new AbortController().signal;
    await fetchDiscovery("202701", " calculus 1 ", 20, signal);
    const url = new URL(String(fetchMock.mock.calls[0]?.[0]));
    expect(url.pathname).toBe("/api/v1/search");
    expect(Object.fromEntries(url.searchParams)).toEqual({ term: "202701", q: " calculus 1 ", offset: "20", limit: "20" });
    expect(fetchMock.mock.calls[0]?.[1]?.signal).toBe(signal);
  });

  test("keeps the selected course and stored instructor name in history requests", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://localhost:8000");
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const { fetchHistory } = await import("./rankings");
    const signal = new AbortController().signal;
    await fetchHistory("202701", 42, "J. Smith", 40, signal);
    const url = new URL(String(fetchMock.mock.calls[0]?.[0]));
    expect(url.pathname).toBe("/api/v1/search/history");
    expect(Object.fromEntries(url.searchParams)).toEqual({ term: "202701", course_id: "42", name: "J. Smith", offset: "40", limit: "20" });
    expect(fetchMock.mock.calls[0]?.[1]?.signal).toBe(signal);
  });

  test("preserves explicit frontend-only fixture course searches and declines absent raw history", async () => {
    vi.stubEnv("VITE_USE_MOCK_DATA", "true");
    vi.stubEnv("VITE_API_BASE_URL", "");
    const fetchMock = vi.fn<typeof fetch>();
    vi.stubGlobal("fetch", fetchMock);
    const { fetchDiscovery, fetchHistory } = await import("./rankings");
    const signal = new AbortController().signal;
    const result = await fetchDiscovery("202701", "ENC 1101", 0, signal);
    expect(result.kind).toBe("course");
    expect(result.courses[0]?.subject).toBe("ENC");
    expect(result.identity_note).toMatch(/Synthetic/);
    await expect(fetchHistory("202701", 1, null, 0, signal)).rejects.toThrow(/unavailable/);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  vi.resetModules();
});

describe("ranking API client", () => {
  test("loads term metadata from the terms endpoint", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://localhost:8000/");
    const terms = [
      { term: "202701", term_name: "Spring 2027", year: 2027, season: "Spring" },
    ];
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(JSON.stringify(terms), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const { fetchTerms } = await import("./rankings");

    await expect(fetchTerms()).resolves.toEqual(terms);
    expect(new URL(String(fetchMock.mock.calls[0]?.[0])).pathname).toBe(
      "/api/v1/metadata/terms",
    );
  });

  test("loads subject metadata from the subjects endpoint", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://localhost:8000");
    const subjects = [{ subject: "ENC" }, { subject: "MAC" }];
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(JSON.stringify(subjects), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const { fetchSubjects } = await import("./rankings");

    await expect(fetchSubjects()).resolves.toEqual(subjects);
    expect(new URL(String(fetchMock.mock.calls[0]?.[0])).pathname).toBe(
      "/api/v1/metadata/subjects",
    );
  });

  test("sends selected search filters to the real API", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://localhost:8000");
    const payload: RankingsSearchResponse = {
      items: syntheticRankings.slice(0, 1),
      total: 1,
      limit: 50,
      offset: 0,
    };
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const { fetchRankings } = await import("./rankings");

    const result = await fetchRankings({
      ...baseQuery,
      subject: "MAC",
      course_number: "1105",
      gened_code: "SMEL",
      delivery_method: "HB",
      seats_open: true,
      min_easiness: 7.5,
      confidence: "medium",
      sort: "course",
    });

    expect(result).toEqual(payload);
    const requestUrl = new URL(String(fetchMock.mock.calls[0]?.[0]));
    expect(requestUrl.pathname).toBe("/api/v1/rankings/search");
    expect(Object.fromEntries(requestUrl.searchParams)).toMatchObject({
      term: "202701",
      subject: "MAC",
      course_number: "1105",
      gened_code: "SMEL",
      delivery_method: "HB",
      seats_open: "true",
      min_easiness: "7.5",
      confidence: "medium",
      sort: "course",
    });
  });

  test("sends limit and offset for pagination", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://localhost:8000");
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(
        new Response(
          JSON.stringify({ items: [], total: 143, limit: 25, offset: 50 }),
          { status: 200 },
        ),
      ),
    );
    const { fetchRankings } = await import("./rankings");

    await fetchRankings({ term: "202701", limit: 25, offset: 50 });

    const fetchMock = vi.mocked(fetch);
    const requestUrl = new URL(String(fetchMock.mock.calls[0]?.[0]));
    expect(requestUrl.searchParams.get("limit")).toBe("25");
    expect(requestUrl.searchParams.get("offset")).toBe("50");
  });

  test("throws for a non-successful API response", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://localhost:8000");
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 503 })),
    );
    const { fetchRankings } = await import("./rankings");

    await expect(fetchRankings(baseQuery)).rejects.toThrow(
      "API request failed with status 503.",
    );
  });

  test("never falls back to synthetic data when an API base URL is configured", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://localhost:8000");
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockRejectedValue(new TypeError("Network unavailable"));
    vi.stubGlobal("fetch", fetchMock);
    const { fetchRankings, isUsingMockData } = await import("./rankings");

    expect(isUsingMockData).toBe(false);
    await expect(fetchRankings(baseQuery)).rejects.toThrow("Network unavailable");
    expect(fetchMock).toHaveBeenCalledOnce();
  });
});


test.each(["", "https://api.example.test"])("explicit mock flag uses fixtures with URL %s", async (url) => {
  vi.stubEnv("VITE_USE_MOCK_DATA", "true");
  vi.stubEnv("VITE_API_BASE_URL", url);
  const fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  const { fetchRankings, fetchMetadata, isUsingMockData } = await import("./rankings");
  expect(isUsingMockData).toBe(true);
  expect((await fetchRankings(baseQuery)).items).toHaveLength(syntheticRankings.length);
  expect((await fetchMetadata()).subjects.length).toBeGreaterThan(0);
  expect(fetchMock).not.toHaveBeenCalled();
});

test.each([undefined, "false", "TRUE", "1"])("production without URL and mock flag %s fails visibly", async (flag) => {
  vi.stubEnv("PROD", true);
  vi.stubEnv("VITE_USE_MOCK_DATA", flag);
  vi.stubEnv("VITE_API_BASE_URL", "");
  const fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  const { fetchRankings, fetchMetadata, isUsingMockData } = await import("./rankings");
  expect(isUsingMockData).toBe(false);
  await expect(fetchRankings(baseQuery)).rejects.toThrow("API configuration unavailable");
  await expect(fetchMetadata()).rejects.toThrow("API configuration unavailable");
  expect(fetchMock).not.toHaveBeenCalled();
});


test("coverage client uses term query and canonical response", async () => {
  vi.stubEnv("VITE_API_BASE_URL", "https://api.example.test");
  const payload = [{ subject: "CHM", course_number: "2045L", catalog_present: true, section_count: 2, latest_observed_at: null, status: "observed" }];
  const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify(payload)));
  vi.stubGlobal("fetch", fetchMock);
  const { fetchCoverage } = await import("./rankings");
  expect(await fetchCoverage("202801")).toEqual(payload);
  expect(String(fetchMock.mock.calls[0][0])).toBe("https://api.example.test/api/v1/metadata/coverage?term=202801");
});

test("coverage failures never fall back to fixture targets", async () => {
  vi.stubEnv("VITE_API_BASE_URL", "https://api.example.test");
  vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockRejectedValue(new Error("offline")));
  const { fetchCoverage } = await import("./rankings");
  await expect(fetchCoverage("202701")).rejects.toThrow("offline");
});

test("explicit mock coverage includes missing and observed examples", async () => {
  vi.stubEnv("VITE_USE_MOCK_DATA", "true");
  const fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  const { fetchCoverage } = await import("./rankings");
  const result = await fetchCoverage("202701");
  expect(result.some(item => item.status === "observed")).toBe(true);
  expect(result.some(item => !item.catalog_present)).toBe(true);
  expect(result.some(item => item.catalog_present && item.status === "missing")).toBe(true);
  expect(fetchMock).not.toHaveBeenCalled();
});

test("sync status is requested from the API with the term query parameter", async () => {
  vi.stubEnv("VITE_API_BASE_URL", "https://api.example.test");
  const payload = { term: "202701", last_success_at: "2027-01-15T11:56:00Z", is_stale: false, stale_after_seconds: 7200 };
  const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify(payload)));
  vi.stubGlobal("fetch", fetchMock);
  const { fetchSyncStatus } = await import("./rankings");
  expect(await fetchSyncStatus("202701")).toEqual(payload);
  expect(String(fetchMock.mock.calls[0][0])).toBe("https://api.example.test/api/v1/metadata/sync-status?term=202701");
});

test("explicit mock sync status is synthetic and never carries a success time", async () => {
  vi.stubEnv("VITE_USE_MOCK_DATA", "true");
  const fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  const { fetchSyncStatus } = await import("./rankings");
  expect((await fetchSyncStatus("202701")).last_success_at).toBeNull();
  expect(fetchMock).not.toHaveBeenCalled();
});
