import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// jsdom has no scrolling; navigation calls scrollTo.
window.scrollTo = vi.fn() as unknown as typeof window.scrollTo;

afterEach(() => cleanup());
