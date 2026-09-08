export const UNAVAILABLE_TIME = "Unavailable";

// Require an explicit offset: timezone-less dates must not depend on the browser.
const parseTimestamp = (value: string | null | undefined): number | null => {
  if (!value || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(value)) return null;
  const [year, month, day] = value.slice(0, 10).split("-").map(Number);
  const leapYear = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const daysInMonth = [31, leapYear ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if (month < 1 || month > 12 || day < 1 || day > daysInMonth[month - 1] || Number(value.slice(11, 13)) > 23) return null;
  const milliseconds = Date.parse(value);
  return Number.isFinite(milliseconds) ? milliseconds : null;
};

export function formatRelativeTime(timestamp: string | null | undefined, now: number = Date.now()): string {
  const observed = parseTimestamp(timestamp);
  if (observed === null || !Number.isFinite(now)) return UNAVAILABLE_TIME;
  // Small clock differences should never produce a negative age.
  const minutes = Math.floor(Math.max(0, now - observed) / 60_000);
  if (minutes === 0) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hr ago`;
  const days = Math.floor(hours / 24);
  return `${days} ${days === 1 ? "day" : "days"} ago`;
}

/** Stable UTC display suitable for a title or tooltip, independent of locale. */
export function formatAbsoluteTime(timestamp: string | null | undefined): string {
  const observed = parseTimestamp(timestamp);
  return observed === null ? UNAVAILABLE_TIME : new Date(observed).toISOString().replace("T", " ").replace(".000Z", " UTC").replace("Z", " UTC");
}
