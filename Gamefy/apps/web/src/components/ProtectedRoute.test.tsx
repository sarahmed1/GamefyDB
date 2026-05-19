import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"

import { ProtectedRoute } from "./ProtectedRoute"

const MOCK_USER = {
  id: "user-1",
  email: "admin@gamefy.com",
  is_active: true,
  is_superuser: true,
  is_verified: true,
}

function renderAt(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/login" element={<div>LOGIN-PAGE-SENTINEL</div>} />
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<div>PROTECTED-CHILD-SENTINEL</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe("ProtectedRoute", () => {
  it("renders Loading… while useMe is pending", () => {
    globalThis.fetch = vi.fn(() => new Promise(() => {}))

    renderAt("/")

    expect(screen.getByText("Loading…")).toBeTruthy()
  })

  it("redirects to /login when /api/auth/me returns 401", async () => {
    globalThis.fetch = vi.fn().mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Unauthorized" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    )

    renderAt("/")

    await screen.findByText("LOGIN-PAGE-SENTINEL")
  })

  it("renders child route when /api/auth/me returns a user", async () => {
    globalThis.fetch = vi.fn().mockResolvedValueOnce(
      new Response(JSON.stringify(MOCK_USER), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    )

    renderAt("/")

    await screen.findByText("PROTECTED-CHILD-SENTINEL")
  })
})
