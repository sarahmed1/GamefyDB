import { describe, expect, it, vi } from "vitest"

import { apiFetch } from "./api"

describe("apiFetch", () => {
  it("sends credentials: include and parses JSON on 2xx", async () => {
    globalThis.fetch = vi.fn().mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    )

    const result = await apiFetch<{ ok: boolean }>("/api/anything")

    expect(result).toEqual({ ok: true })
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/anything",
      expect.objectContaining({ credentials: "include" }),
    )
  })

  it("returns undefined on 204 No Content", async () => {
    globalThis.fetch = vi.fn().mockResolvedValueOnce(
      new Response(null, { status: 204 }),
    )

    const result = await apiFetch<void>("/api/auth/logout", { method: "POST" })
    expect(result).toBeUndefined()
  })

  it("throws ApiError with status on non-2xx", async () => {
    globalThis.fetch = vi.fn().mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "nope" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    )

    await expect(apiFetch("/api/protected")).rejects.toMatchObject({
      status: 401,
      message: expect.stringContaining("nope"),
    })
  })

  it("sends form-encoded body when contentType is form", async () => {
    globalThis.fetch = vi.fn().mockResolvedValueOnce(new Response(null, { status: 204 }))

    await apiFetch("/api/auth/login", {
      method: "POST",
      contentType: "form",
      body: { username: "a@b.c", password: "secret" },
    })

    const call = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(call[1].headers["Content-Type"]).toBe("application/x-www-form-urlencoded")
    expect(call[1].body).toBe("username=a%40b.c&password=secret")
  })
})
