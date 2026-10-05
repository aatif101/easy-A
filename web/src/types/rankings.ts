export type ConfidenceLabel = "low" | "medium" | "high";
export type Freshness = "current" | "historical" | "unavailable";
export type ScoreSource = "instructor_course" | "course" | "subject" | "global";
export type PriorLevel = "course" | "subject" | "global";

export interface RankingProvenance {
  freshness: Freshness;
  source: string;
  source_term: string | null;
  detail: string | null;
}

export interface GenEdAttribute {
  code: string;
  label: string;
}

export interface ModalityInfo {
  delivery_method: string | null;
  delivery_label: string | null;
  provenance: RankingProvenance;
}

export type SeatFreshness = "fresh" | "aging" | "stale" | "unavailable";

export interface SeatInfo {
  observed_at: string | null;
  freshness: SeatFreshness;
  age_seconds: number | null;
  capacity: number | null;
  enrollment: number | null;
  seats_remaining: number | null;
  wait_seats_available: number | null;
  provenance: RankingProvenance;
}

export interface RankingSignal {
  signal_type: string;
  value: string;
  confidence: number;
  source: string;
  source_identifier: string;
  source_term: string;
  freshness: Freshness;
  evidence: string;
}

export type InstructorBreakdownStatus = "ready" | "lab_section" | "no_instructor_history";

/** One instructor's observed grade history for a course (mirrors the 10-05 API contract). */
export interface InstructorHistoryRow {
  name: string;
  /** Raw share of A among A-F letter grades, 0-1. */
  a_share: number;
  /** The denominator shown as "{n} grades". */
  effective_n: number;
  term_count: number;
  /** Banner term codes such as "202501". */
  first_term: string;
  last_term: string;
  /** Shrunk easiness score; null when the instructor is not scored. */
  easiness_score: number | null;
  scored: boolean;
  is_current: boolean;
}

export interface InstructorBreakdown {
  status: InstructorBreakdownStatus;
  /** Server-sorted: current first, then effective_n desc, then name asc. */
  instructors: InstructorHistoryRow[];
  /** The section's named instructor, or null for Staff, blank or ambiguous. */
  current_instructor: string | null;
  current_instructor_has_history: boolean;
  /** Instructors under the collapse cutoff, excluding the current one. */
  other_instructor_count: number;
  scoring_min_effective_n: number;
  collapse_min_effective_n: number;
  provenance: RankingProvenance;
}

export interface HistoricalAnalytics {
  easiness_score: number;
  smoothed_withdrawal_rate: number;
  confidence_label: ConfidenceLabel;
  effective_n: number;
  score_source: ScoreSource;
  prior_level: PriorLevel;
  completed_grade_count: number;
  total_grade_count: number;
  withdrawal_count: number;
  section_count: number;
  term_count: number;
  mapped_instructor_section_count: number;
  provenance: RankingProvenance;
  /** Optional so older payloads and fixtures stay valid. */
  instructor_breakdown?: InstructorBreakdown | null;
}

export interface SectionRanking {
  term: string;
  term_name: string;
  crn: string;
  subject: string;
  course_number: string;
  course_title: string;
  instructor: string | null;
  instructor_provenance: RankingProvenance;
  modality: ModalityInfo;
  seats_remaining: number | null;
  seats: SeatInfo;
  gened_attributes: GenEdAttribute[];
  gened_provenance: RankingProvenance;
  easiness_score: number;
  smoothed_withdrawal_rate: number;
  confidence_label: ConfidenceLabel;
  effective_n: number;
  score_source: ScoreSource;
  historical_analytics: HistoricalAnalytics;
  signals: RankingSignal[];
  signal_provenance: RankingProvenance;
  section_provenance: RankingProvenance;
}

export type RankingSort =
  | "easiness_desc"
  | "easiness_asc"
  | "withdrawal_asc"
  | "seats_desc"
  | "course";

export interface RankingQuery {
  term: string;
  subject?: string;
  course_number?: string;
  gened_code?: string;
  delivery_method?: string;
  seats_open?: boolean;
  min_easiness?: number;
  confidence?: ConfidenceLabel;
  sort?: RankingSort;
  limit: number;
  offset: number;
}

export interface RankingsSearchResponse {
  items: SectionRanking[];
  total: number;
  limit: number;
  offset: number;
}

export type RankingLoader = (
  query: RankingQuery,
  signal?: AbortSignal,
) => Promise<RankingsSearchResponse>;

export type SectionLoader = (
  term: string,
  crn: string,
  signal?: AbortSignal,
) => Promise<SectionRanking | null>;

export type TermsLoader = (signal?: AbortSignal) => Promise<TermMetadata[]>;

export interface TermMetadata {
  term: string;
  term_name: string;
  year: number;
  season: string;
}

export interface SubjectMetadata {
  subject: string;
}

export interface GenEdAttributeMetadata {
  code: string;
  label: string;
}

export interface DeliveryMethodMetadata {
  code: string;
  label: string | null;
}

export interface RankingMetadata {
  terms: TermMetadata[];
  subjects: SubjectMetadata[];
  genedAttributes: GenEdAttributeMetadata[];
  deliveryMethods: DeliveryMethodMetadata[];
}

export type MetadataLoader = (signal?: AbortSignal) => Promise<RankingMetadata>;


export interface CourseCoverage {
  subject: string;
  course_number: string;
  catalog_present: boolean;
  section_count: number;
  latest_observed_at: string | null;
  status: "missing" | "observed";
}

export type CoverageLoader = (term: string, signal?: AbortSignal) => Promise<CourseCoverage[]>;

/** Mirrors the API SyncStatusResponse (GET /api/v1/metadata/sync-status). */
export interface SyncStatus {
  term: string;
  last_success_at: string | null;
  last_run_at: string | null;
  last_status: "succeeded" | "failed" | null;
  last_error_kind: string | null;
  last_records_failed: number | null;
  failures_last_24h: number;
  in_registration_window: boolean;
  cadence_seconds: number;
  stale_after_seconds: number;
  is_stale: boolean;
  as_of: string;
}

export type SyncStatusLoader = (term: string, signal?: AbortSignal) => Promise<SyncStatus>;
