import { parseSearch } from "./search";

export interface InstructorSelection {
  courseId: number;
  name: string;
}

export type Route =
  | { view: "home" }
  | { view: "search"; q: string; instructor?: InstructorSelection }
  | { view: "gened"; area: string };

/** Routes live in the query string so links are shareable and Back works on a static host. */
export const readRoute = (search: string): Route => {
  const params = new URLSearchParams(search);
  const q = params.get("q")?.trim();
  if (q) {
    const name = params.get("instructor")?.trim();
    const courseId = Number(params.get("course_id"));
    if (parseSearch(q).kind === "course" && name && name.length <= 255 && Number.isSafeInteger(courseId) && courseId > 0 && courseId <= 2_147_483_647) {
      return { view: "search", q, instructor: { courseId, name } };
    }
    return { view: "search", q };
  }
  const area = params.get("gened")?.trim().toLowerCase();
  if (area) return { view: "gened", area };
  return { view: "home" };
};

export const routeHref = (route: Route): string => {
  if (route.view === "search") {
    const filter = route.instructor;
    return `?q=${encodeURIComponent(route.q)}` + (filter ? `&course_id=${filter.courseId}&instructor=${encodeURIComponent(filter.name)}` : "");
  }
  if (route.view === "gened") return `?gened=${encodeURIComponent(route.area)}`;
  return window.location.pathname;
};

/** Plain-click handler for an <a href> that should navigate in-app; modified clicks open normally. */
export const inAppClick =
  (navigate: (route: Route) => void, route: Route) =>
  (event: { metaKey: boolean; ctrlKey: boolean; shiftKey: boolean; button: number; preventDefault: () => void }) => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
    event.preventDefault();
    navigate(route);
  };
