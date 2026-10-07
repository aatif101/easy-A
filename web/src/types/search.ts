export interface CourseMatch {
  course_id: number;
  subject: string;
  course_number: string;
  title: string;
  catalog_edition: string;
  current_sections: number;
}
export interface InstructorMatch extends CourseMatch {
  name: string;
  historical_sections: number;
  observed_at: string;
}
export interface DiscoveryResponse {
  as_of: string;
  kind: string;
  subject: string;
  course_number: string;
  crn: string | null;
  courses: CourseMatch[];
  instructors: InstructorMatch[];
  course_total: number;
  instructor_total: number;
  limit: number;
  offset: number;
  identity_note: string;
}
export interface HistoryResponse {
  course: CourseMatch;
  name: string | null;
  status: string;
  a_share: number | null;
  observed_grade_count: number;
  counts: Record<string, number>;
  terms: string[];
  items: { term: string; crn: string; counts: Record<string, number>; source: string; source_hash: string; ingested_at: string }[];
  total: number;
  limit: number;
  offset: number;
  identity_note: string;
}
export type DiscoveryLoader = (term: string, q: string, offset: number, signal: AbortSignal) => Promise<DiscoveryResponse>;
export type HistoryLoader = (term: string, courseId: number, name: string | null, offset: number, signal: AbortSignal) => Promise<HistoryResponse>;
