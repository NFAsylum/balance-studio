import "@testing-library/jest-dom/vitest";

// jsdom polyfills that Radix primitives (Slider, Select) rely on.
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(globalThis as any).ResizeObserver = ResizeObserverMock;

for (const method of ["hasPointerCapture", "setPointerCapture", "releasePointerCapture", "scrollIntoView"] as const) {
  if (!(method in Element.prototype)) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (Element.prototype as any)[method] = () => (method === "hasPointerCapture" ? false : undefined);
  }
}
