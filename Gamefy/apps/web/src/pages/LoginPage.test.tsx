import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import React from "react"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"

import { LoginPage } from "./LoginPage"

function renderLogin() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe("LoginPage", () => {
  it("renders email and password inputs and a submit button", () => {
    globalThis.fetch = vi.fn()
    renderLogin()

    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument()
  })

  it("shows validation errors on empty submit without calling fetch", async () => {
    globalThis.fetch = vi.fn()
    const user = userEvent.setup()
    renderLogin()

    await user.click(screen.getByRole("button", { name: /sign in/i }))

    await waitFor(() => {
      expect(screen.getByText("Enter a valid email")).toBeInTheDocument()
      expect(screen.getByText("Password is required")).toBeInTheDocument()
    })

    expect(globalThis.fetch).not.toHaveBeenCalled()
  })

  it("calls fetch with form-encoded body containing email as username on successful login", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    globalThis.fetch = fetchMock

    const user = userEvent.setup()
    renderLogin()

    await user.type(screen.getByLabelText(/email/i), "admin@gamefy.com")
    await user.type(screen.getByLabelText(/password/i), "secret123")
    await user.click(screen.getByRole("button", { name: /sign in/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/auth/login",
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({
            "Content-Type": "application/x-www-form-urlencoded",
          }),
          body: expect.stringContaining("username=admin%40gamefy.com"),
        }),
      )
    })

    const callBody = fetchMock.mock.calls[0][1].body as string
    expect(callBody).toContain("password=secret123")
  })

  it("renders 'Invalid email or password' when server returns 401", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "LOGIN_BAD_CREDENTIALS" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    )
    globalThis.fetch = fetchMock

    const user = userEvent.setup()
    renderLogin()

    await user.type(screen.getByLabelText(/email/i), "wrong@example.com")
    await user.type(screen.getByLabelText(/password/i), "badpassword")
    await user.click(screen.getByRole("button", { name: /sign in/i }))

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Invalid email or password")
    })
  })
})
