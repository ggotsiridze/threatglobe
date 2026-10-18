import "@testing-library/jest-dom/vitest";

// jsdom has no layout engine; Recharts' ResponsiveContainer needs this API.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver ??= ResizeObserverStub as unknown as typeof ResizeObserver;
