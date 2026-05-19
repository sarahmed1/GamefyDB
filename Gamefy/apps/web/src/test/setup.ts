import "@testing-library/jest-dom/vitest"
import { cleanup } from "@testing-library/react"
import { afterEach, beforeEach, vi } from "vitest"

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

beforeEach(() => {
  // @ts-expect-error - reset fetch so each test must mock it explicitly
  globalThis.fetch = undefined
})
