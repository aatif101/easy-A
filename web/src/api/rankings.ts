import { syntheticRankings } from "../fixtures/rankings";
import type {
  DeliveryMethodMetadata,
  GenEdAttributeMetadata,
  MetadataLoader,
  RankingLoader,
  RankingMetadata,
  RankingQuery,
  RankingsSearchResponse,
  SectionRanking,
  SubjectMetadata,
  TermMetadata,
} from "../types/rankings";

const trimTrailingSlash = (value: string): string => value.replace(/\/+$/, "");

export const apiBaseUrl = trimTrailingSlash(import.meta.env.VITE_API_BASE_URL?.trim() ?? "");
export const isUsingMockData = apiBaseUrl.length === 0;

const endpointUrl = (path: string): URL => new URL(`${apiBaseUrl}${path}`);

const fetchJson = async <Result>(url: URL, signal?: AbortSignal): Promise<Result> => {
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) {
    throw new Error(`API request failed with status ${response.status}.`);
  }
  return (await response.json()) as Result;
};

const mockTerms: TermMetadata[] = [
  { term: "202701", term_name: "Spring 2027", year: 2027, season: "Spring" },
];

const uniqueBy = <Item, Key>(items: Item[], keyFor: (item: Item) => Key): Item[] => {
  const seen = new Set<Key>();
  return items.filter((item) => {
    const key = keyFor(item);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
};

const mockMetadata: RankingMetadata = {
  terms: mockTerms,
  subjects: uniqueBy(
    syntheticRankings.map(({ subject }) => ({ subject })),
    ({ subject }) => subject,
  ).toSorted((left, right) => left.subject.localeCompare(right.subject)),
  genedAttributes: uniqueBy(
    syntheticRankings.flatMap(({ gened_attributes }) => gened_attributes),
    ({ code, label }) => `${code}:${label}`,
  ).toSorted((left, right) => left.code.localeCompare(right.code)),
  deliveryMethods: uniqueBy(
    syntheticRankings.flatMap(({ modality }) =>
      modality.delivery_method
        ? [{ code: modality.delivery_method, label: modality.delivery_label }]
        : [],
    ),
    ({ code }) => code,
  ).toSorted((left, right) => left.code.localeCompare(right.code)),
};

export const fetchTerms = async (signal?: AbortSignal): Promise<TermMetadata[]> => {
  if (isUsingMockData) return mockMetadata.terms;
  return fetchJson<TermMetadata[]>(endpointUrl("/api/v1/metadata/terms"), signal);
};

export const fetchSubjects = async (signal?: AbortSignal): Promise<SubjectMetadata[]> => {
  if (isUsingMockData) return mockMetadata.subjects;
  return fetchJson<SubjectMetadata[]>(endpointUrl("/api/v1/metadata/subjects"), signal);
};

export const fetchGenEdAttributes = async (
  signal?: AbortSignal,
): Promise<GenEdAttributeMetadata[]> => {
  if (isUsingMockData) return mockMetadata.genedAttributes;
  return fetchJson<GenEdAttributeMetadata[]>(
    endpointUrl("/api/v1/metadata/gened-attributes"),
    signal,
  );
};

export const fetchDeliveryMethods = async (
  signal?: AbortSignal,
): Promise<DeliveryMethodMetadata[]> => {
  if (isUsingMockData) return mockMetadata.deliveryMethods;
  return fetchJson<DeliveryMethodMetadata[]>(
    endpointUrl("/api/v1/metadata/delivery-methods"),
    signal,
  );
};

export const fetchMetadata: MetadataLoader = async (signal) => {
  const [terms, subjects, genedAttributes, deliveryMethods] = await Promise.all([
    fetchTerms(signal),
    fetchSubjects(signal),
    fetchGenEdAttributes(signal),
    fetchDeliveryMethods(signal),
  ]);
  return { terms, subjects, genedAttributes, deliveryMethods };
};

const matchesMockQuery = (ranking: SectionRanking, query: RankingQuery): boolean =>
  ranking.term === query.term &&
  (!query.subject || ranking.subject === query.subject.toUpperCase()) &&
  (!query.course_number || ranking.course_number === query.course_number.toUpperCase()) &&
  (!query.gened_code ||
    ranking.gened_attributes.some(({ code }) => code.toUpperCase() === query.gened_code?.toUpperCase())) &&
  (!query.delivery_method ||
    ranking.modality.delivery_method?.toUpperCase() === query.delivery_method.toUpperCase()) &&
  (!query.seats_open || (ranking.seats_remaining ?? 0) > 0) &&
  (query.min_easiness === undefined || ranking.easiness_score >= query.min_easiness) &&
  (!query.confidence || ranking.confidence_label === query.confidence);

const sortMockRankings = (items: SectionRanking[], sort = "easiness_desc"): SectionRanking[] =>
  items.toSorted((left, right) => {
    if (sort === "easiness_asc") return left.easiness_score - right.easiness_score;
    if (sort === "withdrawal_asc") {
      return left.smoothed_withdrawal_rate - right.smoothed_withdrawal_rate;
    }
    if (sort === "seats_desc") {
      return (right.seats_remaining ?? -1) - (left.seats_remaining ?? -1);
    }
    if (sort === "course") {
      return `${left.subject} ${left.course_number}`.localeCompare(
        `${right.subject} ${right.course_number}`,
      );
    }
    return right.easiness_score - left.easiness_score;
  });

export const fetchRankings: RankingLoader = async (query, signal) => {
  if (isUsingMockData) {
    const matching = sortMockRankings(
      syntheticRankings.filter((ranking) => matchesMockQuery(ranking, query)),
      query.sort,
    );
    return {
      items: matching.slice(query.offset, query.offset + query.limit),
      total: matching.length,
      limit: query.limit,
      offset: query.offset,
    };
  }

  const url = endpointUrl("/api/v1/rankings/search");
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== false && value !== "") {
      url.searchParams.set(key, String(value));
    }
  }
  return fetchJson<RankingsSearchResponse>(url, signal);
};
