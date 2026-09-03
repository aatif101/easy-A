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

export interface SeatInfo {
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

export interface RankingQuery {
  term: string;
}

export type RankingLoader = (
  query: RankingQuery,
  signal?: AbortSignal,
) => Promise<SectionRanking[]>;
