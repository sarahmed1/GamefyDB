import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"

import { TopBar } from "./TopBar"

const MOCK_USER = {
  id: "user-1",
  email: "admin@gamefy.com",
  is_active: true,
  is_superuser: true,
  is_verified: true,
}

function renderAt(path: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/login" element={<div>LOGIN-SENTINEL</div>} />
          <Route path="*" element={<TopBar />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe("TopBar", () => {
  it("renders the title matching the current path", () => {
    globalThis.fetch = vi.fn(() => new Promise<Response>(() => {}))

    renderAt("/cash")

    expect(screen.getByRole("heading", { name: "Cash transactions" })).toBeTruthy()
  })

  it("shows email when useMe returns a user", async () => {
    globalThis.fetch = vi.fn().mockResolvedValueOnce(
      new Response(JSON.stringify(MOCK_USER), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    )

    renderAt("/")

    await screen.findByText("admin@gamefy.com")
  })

  it("clicking Sign out calls /api/auth/logout and navigates to /login", async () => {
    // First fetch: useMe → user; second fetch: logout POST
    globalThis.fetch = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify(MOCK_USER), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(new Response(null, { status: 204 }))

    const user = userEvent.setup()
    renderAt("/")

    // Wait for the user email to appear (me query resolved)
    await screen.findByText("admin@gamefy.com")

    await user.click(screen.getByRole("button", { name: /sign out/i }))

    await waitFor(() => {
      expect(screen.getByText("LOGIN-SENTINEL")).toBeTruthy()
    })

    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/auth/logout",
      expect.objectContaining({ method: "POST" }),
    )
  })
})
