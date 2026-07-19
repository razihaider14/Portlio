import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll, expect } from "vitest";
import { toHaveNoViolations } from "jest-axe";
import { server } from "@/test/msw/server";

declare module "vitest" {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  interface Assertion<T = any> {
    toHaveNoViolations(): T;
  }
}

// jest-axe's matcher is written against Jest's `expect.extend` API, which
// Vitest's `expect` is deliberately compatible with, this registers
// `expect(container).toHaveNoViolations()` for the accessibility tests.
expect.extend(toHaveNoViolations);

// onUnhandledRequest: "bypass" so tests that mock lib/api/endpoints or
// lib/api/client directly (i.e. never actually call fetch) aren't affected
// by MSW at all, only tests that genuinely hit the network go through it.
beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// jsdom doesn't implement matchMedia; next-themes calls it to resolve the
// "system" theme. Without this, any test that renders <ThemeProvider>
// throws "window.matchMedia is not a function".
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});

afterEach(() => {
  cleanup();
});
