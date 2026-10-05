export type ParsedSearch =
  | { kind: "crn"; crn: string }
  | { kind: "course"; subject: string; courseNumber: string }
  | { kind: "subject"; subject: string }
  | { kind: "unknown"; text: string }
  | { kind: "empty" };

/** Reads the one search box the way OASIS users type: a CRN, a course code, or a subject. */
export const parseSearch = (value: string): ParsedSearch => {
  const text = value.trim().toUpperCase();
  if (!text) return { kind: "empty" };
  if (/^\d{5}$/.test(text)) return { kind: "crn", crn: text };
  const course = text.match(/^([A-Z]{3})\s*-?\s*(\d{4}[A-Z]?)$/);
  if (course) return { kind: "course", subject: course[1], courseNumber: course[2] };
  if (/^[A-Z]{3}$/.test(text)) return { kind: "subject", subject: text };
  return { kind: "unknown", text: value.trim() };
};

export interface GenEdArea {
  id: string;
  label: string;
  /** Schedule attribute codes that satisfy the area: the state core and USF's own Gen Ed. */
  codes: string[];
}

export const GEN_ED_AREAS: GenEdArea[] = [
  { id: "communication", label: "Communication", codes: ["SGEC", "UGEC"] },
  { id: "mathematics", label: "Mathematics", codes: ["SGEM", "UGEM"] },
  { id: "natural-sciences", label: "Natural Sciences", codes: ["SGEN", "UGEN"] },
  { id: "social-sciences", label: "Social Sciences", codes: ["SGES", "UGES"] },
  { id: "humanities", label: "Humanities", codes: ["SGEH", "UGEH"] },
  { id: "civics", label: "Civics Literacy", codes: ["SCIV"] },
];

export const findGenEdArea = (id: string): GenEdArea | undefined =>
  GEN_ED_AREAS.find((area) => area.id === id.toLowerCase());

/** Attribute codes worth naming on a course page: Gen Ed areas and the state requirements. */
export const REQUIREMENT_CODES = new Set(["6AC", "6AM", ...GEN_ED_AREAS.flatMap(({ codes }) => codes)]);
