import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { renderHook, waitFor } from "@testing-library/react"
import React from "react"
import { describe, expect, it, vi } from "vitest"

import { useLogin, useLogout, useMe } from "./auth"

function makeWrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
}

const MOCK_USER = {
  id: "user-1",
  email: "admin@gamefy.com",
  is_active: true,
  is_superuser: true,
  is_verified: true,
}

describe("useMe", () => {
  it("returns null when /api/auth/me returns 401", async () => {
    globalThis.fetch = vi.fn().mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Unauthorized" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    )

    const { result } = renderHook(() => useMe(), { wrapper: makeWrapper() })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toBeNull()
  })

  it("returns the user object when /api/auth/me returns 200", async () => {
    globalThis.fetch = vi.fn().mockResolvedValueOnce(
      new Response(JSON.stringify(MOCK_USER), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    )

    const { result } = renderHook(() => useMe(), { wrapper: makeWrapper() })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(MOCK_USER)
  })
})

describe("useLogin", () => {
  it("posts form-encoded body then useMe re-queries and returns the user", async () => {
    const fetchMock = vi
      .fn()
      // 1. initial useMe fetch → 401 (not logged in)
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "Unauthorized" }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        }),
      )
      // 2. login POST → 204
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      // 3. useMe refetch after invalidation → 200 with user
      .mockResolvedValueOnce(
        new Response(JSON.stringify(MOCK_USER), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )

    globalThis.fetch = fetchMock

    const wrapper = makeWrapper()
    const meHook = renderHook(() => useMe(), { wrapper })
    const loginHook = renderHook(() => useLogin(), { wrapper })

    // Wait for initial useMe to settle as null
    await waitFor(() => expect(meHook.result.current.isSuccess).toBe(true))
    expect(meHook.result.current.data).toBeNull()

    // Trigger login
    loginHook.result.current.mutate({ username: "admin@gamefy.com", password: "secret" })

    // Wait for login to succeed
    await waitFor(() => expect(loginHook.result.current.isSuccess).toBe(true))

    // Verify the login request was form-encoded
    const loginCall = fetchMock.mock.calls[1]
    expect(loginCall[0]).toBe("/api/auth/login")
    expect(loginCall[1].headers["Content-Type"]).toBe("application/x-www-form-urlencoded")
    expect(loginCall[1].body).toContain("username=admin%40gamefy.com")
    expect(loginCall[1].body).toContain("password=secret")

    // Wait for useMe to refetch and return the user
    await waitFor(() => expect(meHook.result.current.data).toEqual(MOCK_USER))
  })
})

describe("useLogout", () => {
  it("posts to /api/auth/logout and clears the useMe cache to null", async () => {
    // Step 1: prime cache — useMe fetches successfully
    globalThis.fetch = vi.fn().mockResolvedValueOnce(
      new Response(JSON.stringify(MOCK_USER), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    )

    const wrapper = makeWrapper()
    const meHook = renderHook(() => useMe(), { wrapper })
    const logoutHook = renderHook(() => useLogout(), { wrapper })

    await waitFor(() => expect(meHook.result.current.data).toEqual(MOCK_USER))

    // Step 2: set up logout fetch → 204
    globalThis.fetch = vi.fn().mockResolvedValueOnce(new Response(null, { status: 204 }))

    // Trigger logout
    logoutHook.result.current.mutate()

    // Wait for logout to succeed and cache to be null
    await waitFor(() => expect(logoutHook.result.current.isSuccess).toBe(true))
    await waitFor(() => expect(meHook.result.current.data).toBeNull())

    // Verify logout endpoint was called correctly
    const logoutFetch = globalThis.fetch as ReturnType<typeof vi.fn>
    expect(logoutFetch.mock.calls[0][0]).toBe("/api/auth/logout")
    expect(logoutFetch.mock.calls[0][1].method).toBe("POST")
  })
})
