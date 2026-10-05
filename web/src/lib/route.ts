export type Route =
  | { view: "home" }
  | { view: "search"; q: string }
  | { view: "gened"; area: string };

/** Routes live in the query string so links are shareable and Back works on a static host. */
export const readRoute = (search: string): Route => {
  const params = new URLSearchParams(search);
  const q = params.get("q")?.trim();
  if (q) return { view: "search", q };
  const area = params.get("gened")?.trim().toLowerCase();
  if (area) return { view: "gened", area };
  return { view: "home" };
};

export const routeHref = (route: Route): string => {
  if (route.view === "search") return `?q=${encodeURIComponent(route.q)}`;
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
