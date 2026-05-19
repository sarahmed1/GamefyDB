import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"

import { AppShell } from "./AppShell"

const MOCK_USER = {
  id: "u1",
  email: "admin@gamefy.com",
  is_active: true,
  is_superuser: true,
  is_verified: true,
}

function renderShell() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  globalThis.fetch = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(MOCK_USER), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  )
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route element={<AppShell />}>
            <Route path="/" element={<div>SHELL-CHILD-SENTINEL</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe("AppShell", () => {
  it("renders the IconRail nav, a TopBar heading, and the child route content", async () => {
    renderShell()

    // IconRail renders a <nav> with aria-label
    expect(screen.getByRole("navigation", { name: /primary navigation/i })).toBeTruthy()

    // TopBar renders an <h1> for the current path "/"
    expect(screen.getByRole("heading", { name: "Dashboard" })).toBeTruthy()

    // Child route sentinel is rendered via <Outlet />
    expect(screen.getByText("SHELL-CHILD-SENTINEL")).toBeTruthy()
  })
})
