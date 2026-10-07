const USF_PROFESSOR_SEARCH = "https://www.ratemyprofessors.com/search/professors/1262";
const PLACEHOLDER = /^(staff|tba|tbd|unknown|unavailable|not available|not announced|ambiguous|n\/?a|[-–—])$/i;

/** A school-scoped search, never a verified professor profile. */
export function rmpSearchUrl(instructor: string | null | undefined): string | null {
  const name = instructor?.trim();
  // Multiple names cannot be searched as one professor. Commas and apostrophes are valid.
  if (!name || PLACEHOLDER.test(name) || /[/;|&\r\n]|\s+and\s+/i.test(name)) return null;
  return `${USF_PROFESSOR_SEARCH}?q=${encodeURIComponent(name)}`;
}
