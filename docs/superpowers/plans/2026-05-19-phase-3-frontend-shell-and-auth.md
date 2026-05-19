# Phase 3 — Frontend Shell + Auth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the React + Vite + React Router v7 frontend with a cookie-based auth flow that talks to the Phase 1 backend, so an admin can log in via the browser and see the icon-rail shell with an empty canvas.

**Architecture:** Vite proxies `/api/*` to the FastAPI server on `:8000`; the SPA boots into a TanStack-Query-backed `useMe()` hook that calls `GET /api/auth/me`; a `<ProtectedRoute>` redirects unauthenticated users to `/login`; the icon-rail `<AppShell>` wraps every authenticated route with `<Outlet/>` for child content. Frontend tests are Vitest + React Testing Library with `fetch` mocked at the module boundary — no MSW, no Playwright in this phase (Playwright e2e is deferred to a later phase).

**Tech Stack:** React 19 + TypeScript, Vite 7, React Router v7, TanStack Query v5, react-hook-form + zod, sonner, lucide-react, shadcn primitives (`button` exists; we add `input`, `label`, `card`), Vitest + @testing-library/react + jsdom.

**Spec deviations (documented; do not "fix"):**

- Playwright is out of scope for this phase. The spec calls for 1 Playwright smoke test; we defer it to the same phase that introduces real chart rendering (Phase 4).
- The user menu in the TopBar is a plain `<Button>` (logout button) rather than a `DropdownMenu`. Adding `dropdown-menu` is out of scope.
- The date-range picker in the TopBar is **not** built in Phase 3 — the spec attaches it to the TopBar but it only becomes useful when fact/KPI pages exist (Phase 4+).

---

## File Structure

**Working directory for all frontend work:** `C:\Users\sarah\GamefyDB\Gamefy\apps\web` (the bun workspace for the SPA). Run `bun` commands from that directory unless noted.

**Create:**

- `Gamefy/apps/web/vitest.config.ts` — Vitest config with jsdom env
- `Gamefy/apps/web/src/test/setup.ts` — RTL setup, `cleanup()` hook, fetch mock helpers
- `Gamefy/apps/web/src/lib/api.ts` — typed `fetch` wrapper (`credentials: "include"`, JSON, throw on non-2xx)
- `Gamefy/apps/web/src/lib/api.test.ts`
- `Gamefy/apps/web/src/lib/auth.ts` — `useMe`, `useLogin`, `useLogout`
- `Gamefy/apps/web/src/lib/auth.test.tsx`
- `Gamefy/apps/web/src/lib/query-client.ts` — single configured QueryClient
- `Gamefy/apps/web/src/pages/login.tsx`
- `Gamefy/apps/web/src/pages/login.test.tsx`
- `Gamefy/apps/web/src/pages/placeholders.tsx` — empty-canvas components per section
- `Gamefy/apps/web/src/components/shell/app-shell.tsx`
- `Gamefy/apps/web/src/components/shell/top-bar.tsx`
- `Gamefy/apps/web/src/components/shell/icon-rail.tsx`
- `Gamefy/apps/web/src/components/shell/protected-route.tsx`
- `Gamefy/apps/web/src/components/shell/protected-route.test.tsx`
- `Gamefy/apps/web/src/router.tsx` — React Router v7 route tree
- `Gamefy/packages/ui/src/components/input.tsx`
- `Gamefy/packages/ui/src/components/label.tsx`
- `Gamefy/packages/ui/src/components/card.tsx`

**Modify:**

- `Gamefy/apps/web/package.json` — add runtime + test deps + `test` script
- `Gamefy/packages/ui/package.json` — add `@radix-ui/react-label` runtime dep
- `Gamefy/apps/web/vite.config.ts` — add `/api → http://localhost:8000` proxy
- `Gamefy/apps/web/tsconfig.app.json` — add vitest globals (`"types": ["vitest/globals"]`)
- `Gamefy/apps/web/src/main.tsx` — wrap with `QueryClientProvider`, `RouterProvider`, `Toaster`
- `Gamefy/apps/web/src/App.tsx` — **delete** (replaced by router)
- `CLAUDE.md` — append a frontend quickstart (`bun install`, `bun run dev`, login URL)

---

## Conventions

- **Working dir.** Every `bun` / `npx` / `bunx` command runs from `C:\Users\sarah\GamefyDB\Gamefy\apps\web` unless prefixed with `cd ../../packages/ui`. Test runs and dev server boot use that path.
- **No Co-Authored-By trailer** on commits (project convention).
- **TypeScript only**, no `.js` files. Indent: 2 spaces. Quoting follows the existing scaffold (double quotes, no semicolons in JSX prop strings).
- **TanStack Query keys** are static string arrays — keys for this phase: `["auth", "me"]` only. No factory module yet.
- **`fetch` mocking pattern**: tests assign `global.fetch = vi.fn(...)`; the setup file resets it between tests. No MSW.

---

## Task 1: Install runtime + test dependencies

**Files:**

- Modify: `Gamefy/apps/web/package.json`
- Modify: `Gamefy/packages/ui/package.json`

- [ ] **Step 1: Add runtime deps to `apps/web`**

From `C:\Users\sarah\GamefyDB\Gamefy\apps\web`:

```powershell
bun add react-router-dom@^7 @tanstack/react-query@^5 react-hook-form@^7 @hookform/resolvers@^3 zod@^3 sonner@^1
```

- [ ] **Step 2: Add dev/test deps to `apps/web`**

```powershell
bun add -d vitest@^2 @vitest/ui@^2 @testing-library/react@^16 @testing-library/jest-dom@^6 @testing-library/user-event@^14 jsdom@^25
```

- [ ] **Step 3: Add `@radix-ui/react-label` to `packages/ui`**

From `C:\Users\sarah\GamefyDB\Gamefy\packages\ui`:

```powershell
bun add @radix-ui/react-label@^2
```

(The existing `button.tsx` uses `radix-ui` (the meta package) for `Slot.Root`. Label needs the standalone primitive.)

- [ ] **Step 4: Verify install worked**

From `C:\Users\sarah\GamefyDB\Gamefy\apps\web`:

```powershell
bun pm ls --depth 0
```

Expected: shows `react-router-dom@7.x`, `@tanstack/react-query@5.x`, `vitest@2.x`, `@testing-library/react@16.x`, `jsdom@25.x`, etc.

- [ ] **Step 5: Commit (from repo root)**

From `C:\Users\sarah\GamefyDB`:

```powershell
git add Gamefy/apps/web/package.json Gamefy/packages/ui/package.json Gamefy/bun.lock
git commit -m "feat(web): add router, query, test, and form dependencies"
```

---

## Task 2: Vite proxy + Vitest config + test setup

**Files:**

- Modify: `Gamefy/apps/web/vite.config.ts`
- Create: `Gamefy/apps/web/vitest.config.ts`
- Create: `Gamefy/apps/web/src/test/setup.ts`
- Modify: `Gamefy/apps/web/tsconfig.app.json`
- Modify: `Gamefy/apps/web/package.json` (add `test` script)

- [ ] **Step 1: Add the dev-server proxy to `vite.config.ts`**

Replace `Gamefy/apps/web/vite.config.ts` with:

```ts
import path from "path"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: false,
      },
    },
  },
})
```

- [ ] **Step 2: Create `vitest.config.ts`**

Create `Gamefy/apps/web/vitest.config.ts`:

```ts
import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vitest/config"

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
})
```

(Vitest has its own config so we don't pull tailwind/PostCSS into every test run.)

- [ ] **Step 3: Create `src/test/setup.ts`**

Create `Gamefy/apps/web/src/test/setup.ts`:

```ts
import "@testing-library/jest-dom/vitest"
import { cleanup } from "@testing-library/react"
import { afterEach, beforeEach, vi } from "vitest"

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

beforeEach(() => {
  // Each test that needs fetch must assign global.fetch itself.
  // We just make sure the previous test's mock is wiped.
  // (vi.restoreAllMocks() above handles vi.fn() calls; plain assignments
  // get cleared here.)
  // @ts-expect-error - jsdom doesn't type global.fetch
  globalThis.fetch = undefined
})
```

- [ ] **Step 4: Update `tsconfig.app.json` to include vitest globals**

Read `Gamefy/apps/web/tsconfig.app.json` first. Then add `"vitest/globals"` to the `compilerOptions.types` array (create the field if it doesn't exist). Example final shape (merge with existing fields — do not overwrite the file blindly):

```json
{
  "compilerOptions": {
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  }
}
```

- [ ] **Step 5: Add a `test` script to `apps/web/package.json`**

In the `scripts` object of `Gamefy/apps/web/package.json`, add:

```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Step 6: Smoke check Vitest config**

From `C:\Users\sarah\GamefyDB\Gamefy\apps\web`:

```powershell
bun run test
```

Expected: `No test files found, exiting with code 0` (or similar) — Vitest finds the config and exits cleanly. **This is a pass condition.** If Vitest crashes complaining about jsdom or setup, fix before committing.

- [ ] **Step 7: Commit**

From `C:\Users\sarah\GamefyDB`:

```powershell
git add Gamefy/apps/web/vite.config.ts Gamefy/apps/web/vitest.config.ts Gamefy/apps/web/src/test/setup.ts Gamefy/apps/web/tsconfig.app.json Gamefy/apps/web/package.json
git commit -m "feat(web): configure vite api proxy and vitest jsdom env"
```

---

## Task 3: Add `input`, `label`, `card` shadcn primitives

**Files:**

- Create: `Gamefy/packages/ui/src/components/input.tsx`
- Create: `Gamefy/packages/ui/src/components/label.tsx`
- Create: `Gamefy/packages/ui/src/components/card.tsx`

These match the scaffold's `radix-nova` style (compare with the existing `button.tsx`: `data-slot`, `cn`, `cva` patterns).

- [ ] **Step 1: Create `input.tsx`**

```tsx
import * as React from "react"

import { cn } from "@workspace/ui/lib/utils"

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        "border-input bg-background ring-offset-background placeholder:text-muted-foreground flex h-9 w-full rounded-md border px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
        "aria-invalid:border-destructive aria-invalid:ring-destructive/40",
        className,
      )}
      {...props}
    />
  )
}

export { Input }
```

- [ ] **Step 2: Create `label.tsx`**

```tsx
"use client"

import * as React from "react"
import * as LabelPrimitive from "@radix-ui/react-label"

import { cn } from "@workspace/ui/lib/utils"

function Label({
  className,
  ...props
}: React.ComponentProps<typeof LabelPrimitive.Root>) {
  return (
    <LabelPrimitive.Root
      data-slot="label"
      className={cn(
        "text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70",
        className,
      )}
      {...props}
    />
  )
}

export { Label }
```

- [ ] **Step 3: Create `card.tsx`**

```tsx
import * as React from "react"

import { cn } from "@workspace/ui/lib/utils"

function Card({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card"
      className={cn(
        "bg-card text-card-foreground rounded-xl border shadow-sm",
        className,
      )}
      {...props}
    />
  )
}

function CardHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-header"
      className={cn("flex flex-col space-y-1.5 p-6", className)}
      {...props}
    />
  )
}

function CardTitle({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-title"
      className={cn("text-lg font-semibold leading-none tracking-tight", className)}
      {...props}
    />
  )
}

function CardDescription({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-description"
      className={cn("text-muted-foreground text-sm", className)}
      {...props}
    />
  )
}

function CardContent({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div data-slot="card-content" className={cn("p-6 pt-0", className)} {...props} />
  )
}

function CardFooter({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-footer"
      className={cn("flex items-center p-6 pt-0", className)}
      {...props}
    />
  )
}

export { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle }
```

- [ ] **Step 4: Typecheck the ui package**

From `C:\Users\sarah\GamefyDB\Gamefy\packages\ui`:

```powershell
bun run typecheck
```

Expected: 0 errors.

- [ ] **Step 5: Commit**

From `C:\Users\sarah\GamefyDB`:

```powershell
git add Gamefy/packages/ui/src/components/input.tsx Gamefy/packages/ui/src/components/label.tsx Gamefy/packages/ui/src/components/card.tsx
git commit -m "feat(ui): add input, label, and card shadcn primitives"
```

---

## Task 4: `lib/api.ts` — typed fetch wrapper with tests

**Files:**

- Create: `Gamefy/apps/web/src/lib/api.ts`
- Create: `Gamefy/apps/web/src/lib/api.test.ts`

- [ ] **Step 1: Write failing tests**

Create `Gamefy/apps/web/src/lib/api.test.ts`:

```ts
import { describe, expect, it, vi } from "vitest"

import { apiFetch, ApiError } from "./api"

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
```

- [ ] **Step 2: Run tests to confirm failure**

From `C:\Users\sarah\GamefyDB\Gamefy\apps\web`:

```powershell
bun run test src/lib/api.test.ts
```

Expected: 4 fails — module `./api` not found.

- [ ] **Step 3: Implement `lib/api.ts`**

Create `Gamefy/apps/web/src/lib/api.ts`:

```ts
export class ApiError extends Error {
  status: number
  detail: unknown

  constructor(status: number, detail: unknown, message: string) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.detail = detail
  }
}

type ApiFetchOptions = Omit<RequestInit, "body" | "headers"> & {
  body?: unknown
  contentType?: "json" | "form"
  headers?: Record<string, string>
}

export async function apiFetch<T = unknown>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<T> {
  const { body, contentType = "json", headers = {}, ...rest } = options

  const init: RequestInit & { headers: Record<string, string> } = {
    ...rest,
    credentials: "include",
    headers: { ...headers },
  }

  if (body !== undefined) {
    if (contentType === "form") {
      init.headers["Content-Type"] = "application/x-www-form-urlencoded"
      init.body = new URLSearchParams(body as Record<string, string>).toString()
    } else {
      init.headers["Content-Type"] = "application/json"
      init.body = JSON.stringify(body)
    }
  }

  const response = await fetch(path, init)

  if (response.status === 204) {
    return undefined as T
  }

  if (!response.ok) {
    let detail: unknown
    let message = `Request failed with ${response.status}`
    try {
      detail = await response.json()
      if (detail && typeof detail === "object" && "detail" in detail) {
        message = `${message}: ${(detail as { detail: string }).detail}`
      }
    } catch {
      // body was not JSON; leave detail undefined
    }
    throw new ApiError(response.status, detail, message)
  }

  return (await response.json()) as T
}
```

- [ ] **Step 4: Run tests to verify pass**

```powershell
bun run test src/lib/api.test.ts
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

From `C:\Users\sarah\GamefyDB`:

```powershell
git add Gamefy/apps/web/src/lib/api.ts Gamefy/apps/web/src/lib/api.test.ts
git commit -m "feat(web): add apiFetch wrapper with credentials include"
```

---

## Task 5: `lib/auth.ts` — TanStack Query auth hooks with tests

**Files:**

- Create: `Gamefy/apps/web/src/lib/query-client.ts`
- Create: `Gamefy/apps/web/src/lib/auth.ts`
- Create: `Gamefy/apps/web/src/lib/auth.test.tsx`

- [ ] **Step 1: Create the shared QueryClient module**

Create `Gamefy/apps/web/src/lib/query-client.ts`:

```ts
import { QueryClient } from "@tanstack/react-query"

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        retry: false,
        refetchOnWindowFocus: false,
      },
      mutations: {
        retry: false,
      },
    },
  })
}
```

(Single factory so tests get a fresh instance each time.)

- [ ] **Step 2: Write failing tests for the hooks**

Create `Gamefy/apps/web/src/lib/auth.test.tsx`:

```tsx
import { QueryClientProvider } from "@tanstack/react-query"
import { act, renderHook, waitFor } from "@testing-library/react"
import type { ReactNode } from "react"
import { describe, expect, it, vi } from "vitest"

import { useLogin, useLogout, useMe } from "./auth"
import { createQueryClient } from "./query-client"

function wrapper() {
  const client = createQueryClient()
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
}

describe("useMe", () => {
  it("returns the user when /api/auth/me responds 200", async () => {
    globalThis.fetch = vi.fn().mockResolvedValueOnce(
      new Response(
        JSON.stringify({ id: "u1", email: "admin@gamefy.test", role: "admin", is_active: true }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    )

    const { result } = renderHook(() => useMe(), { wrapper: wrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data?.email).toBe("admin@gamefy.test")
    expect(result.current.data?.role).toBe("admin")
  })

  it("isError=true when /api/auth/me responds 401", async () => {
    globalThis.fetch = vi.fn().mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Unauthorized" }), { status: 401 }),
    )

    const { result } = renderHook(() => useMe(), { wrapper: wrapper() })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

describe("useLogin", () => {
  it("posts form-encoded body and invalidates the me query", async () => {
    const fetchSpy = vi
      .fn()
      // initial useMe (not logged in yet): 401
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "Unauthorized" }), { status: 401 }),
      )
      // login: 204
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      // refetch of /api/auth/me triggered by invalidation
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ id: "u1", email: "admin@gamefy.test", role: "admin", is_active: true }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
    globalThis.fetch = fetchSpy

    const Wrapper = wrapper()
    const { result } = renderHook(
      () => ({ login: useLogin(), me: useMe() }),
      { wrapper: Wrapper },
    )

    // Wait for the initial me query to settle (401) before logging in.
    await waitFor(() => expect(result.current.me.isError).toBe(true))

    await act(async () => {
      await result.current.login.mutateAsync({ email: "admin@gamefy.test", password: "secret" })
    })

    expect(fetchSpy.mock.calls[1][0]).toBe("/api/auth/login")
    expect(fetchSpy.mock.calls[1][1].body).toBe("username=admin%40gamefy.test&password=secret")
    expect(fetchSpy.mock.calls[1][1].headers["Content-Type"]).toBe(
      "application/x-www-form-urlencoded",
    )

    await waitFor(() => expect(result.current.me.data?.email).toBe("admin@gamefy.test"))
  })
})

describe("useLogout", () => {
  it("posts to /api/auth/logout and clears the me cache", async () => {
    const fetchSpy = vi
      .fn()
      // first me call (priming): 200
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ id: "u1", email: "x@y.z", role: "viewer", is_active: true }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      // logout: 204
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      // post-logout refetch of me: 401
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "Unauthorized" }), { status: 401 }))
    globalThis.fetch = fetchSpy

    const Wrapper = wrapper()
    const { result } = renderHook(
      () => ({ logout: useLogout(), me: useMe() }),
      { wrapper: Wrapper },
    )

    await waitFor(() => expect(result.current.me.isSuccess).toBe(true))

    await act(async () => {
      await result.current.logout.mutateAsync()
    })

    expect(fetchSpy.mock.calls[1][0]).toBe("/api/auth/logout")
    expect(fetchSpy.mock.calls[1][1].method).toBe("POST")
    await waitFor(() => expect(result.current.me.isError).toBe(true))
  })
})
```

- [ ] **Step 3: Run tests to confirm failure**

```powershell
bun run test src/lib/auth.test.tsx
```

Expected: fails — `./auth` not found.

- [ ] **Step 4: Implement `lib/auth.ts`**

Create `Gamefy/apps/web/src/lib/auth.ts`:

```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { apiFetch } from "./api"

export type Me = {
  id: string
  email: string
  role: string
  is_active: boolean
  is_superuser?: boolean
  is_verified?: boolean
}

const ME_KEY = ["auth", "me"] as const

export function useMe() {
  return useQuery<Me>({
    queryKey: ME_KEY,
    queryFn: () => apiFetch<Me>("/api/auth/me"),
  })
}

export type LoginInput = { email: string; password: string }

export function useLogin() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (input: LoginInput) => {
      await apiFetch<void>("/api/auth/login", {
        method: "POST",
        contentType: "form",
        body: { username: input.email, password: input.password },
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ME_KEY })
    },
  })
}

export function useLogout() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      await apiFetch<void>("/api/auth/logout", { method: "POST" })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ME_KEY })
    },
  })
}
```

- [ ] **Step 5: Run tests to verify pass**

```powershell
bun run test src/lib/auth.test.tsx
```

Expected: 4 passed (1 useMe success, 1 useMe 401, 1 useLogin, 1 useLogout).

- [ ] **Step 6: Commit**

From `C:\Users\sarah\GamefyDB`:

```powershell
git add Gamefy/apps/web/src/lib/query-client.ts Gamefy/apps/web/src/lib/auth.ts Gamefy/apps/web/src/lib/auth.test.tsx
git commit -m "feat(web): add useMe, useLogin, useLogout auth hooks"
```

---

## Task 6: Login page

**Files:**

- Create: `Gamefy/apps/web/src/pages/login.tsx`
- Create: `Gamefy/apps/web/src/pages/login.test.tsx`

- [ ] **Step 1: Write failing test**

Create `Gamefy/apps/web/src/pages/login.test.tsx`:

```tsx
import { QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"

import { createQueryClient } from "@/lib/query-client"
import { LoginPage } from "./login"

function renderLogin() {
  const client = createQueryClient()
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/login"]}>
        <LoginPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe("LoginPage", () => {
  it("renders email and password inputs and a sign-in button", () => {
    renderLogin()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument()
  })

  it("submits credentials to /api/auth/login", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValue(
        new Response(
          JSON.stringify({ id: "u1", email: "admin@gamefy.test", role: "admin", is_active: true }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
    globalThis.fetch = fetchSpy

    renderLogin()
    await userEvent.type(screen.getByLabelText(/email/i), "admin@gamefy.test")
    await userEvent.type(screen.getByLabelText(/password/i), "admin12345")
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }))

    expect(fetchSpy.mock.calls[0][0]).toBe("/api/auth/login")
    expect(fetchSpy.mock.calls[0][1].body).toBe(
      "username=admin%40gamefy.test&password=admin12345",
    )
  })

  it("shows a validation error when email is empty", async () => {
    renderLogin()
    await userEvent.type(screen.getByLabelText(/password/i), "anything")
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }))
    expect(await screen.findByText(/email is required/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to confirm failure**

```powershell
bun run test src/pages/login.test.tsx
```

Expected: fails — module `./login` not found.

- [ ] **Step 3: Implement `LoginPage`**

Create `Gamefy/apps/web/src/pages/login.tsx`:

```tsx
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { Link, useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { z } from "zod"

import { Button } from "@workspace/ui/components/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@workspace/ui/components/card"
import { Input } from "@workspace/ui/components/input"
import { Label } from "@workspace/ui/components/label"

import { ApiError } from "@/lib/api"
import { useLogin } from "@/lib/auth"

const loginSchema = z.object({
  email: z.string().min(1, "Email is required").email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
})

type LoginFormValues = z.infer<typeof loginSchema>

export function LoginPage() {
  const navigate = useNavigate()
  const login = useLogin()

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  })

  const onSubmit = async (values: LoginFormValues) => {
    try {
      await login.mutateAsync(values)
      toast.success("Signed in")
      navigate("/", { replace: true })
    } catch (error) {
      if (error instanceof ApiError && error.status === 400) {
        toast.error("Invalid email or password")
      } else {
        toast.error("Could not sign in. Please try again.")
      }
    }
  }

  return (
    <div className="bg-background flex min-h-svh items-center justify-center p-6">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Sign in to GamefyDB</CardTitle>
          <CardDescription>Use your admin or viewer account.</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4" onSubmit={form.handleSubmit(onSubmit)}>
            <div className="grid gap-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="username"
                aria-invalid={form.formState.errors.email ? true : undefined}
                {...form.register("email")}
              />
              {form.formState.errors.email ? (
                <p className="text-destructive text-xs">
                  {form.formState.errors.email.message}
                </p>
              ) : null}
            </div>

            <div className="grid gap-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                aria-invalid={form.formState.errors.password ? true : undefined}
                {...form.register("password")}
              />
              {form.formState.errors.password ? (
                <p className="text-destructive text-xs">
                  {form.formState.errors.password.message}
                </p>
              ) : null}
            </div>

            <Button type="submit" disabled={login.isPending} className="w-full">
              {login.isPending ? "Signing in…" : "Sign in"}
            </Button>
          </form>

          <p className="text-muted-foreground mt-4 text-xs">
            Don&apos;t have an account?{" "}
            <Link to="/login" className="underline">
              Ask an admin
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
```

- [ ] **Step 4: Run tests to verify pass**

```powershell
bun run test src/pages/login.test.tsx
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

From `C:\Users\sarah\GamefyDB`:

```powershell
git add Gamefy/apps/web/src/pages/login.tsx Gamefy/apps/web/src/pages/login.test.tsx
git commit -m "feat(web): add login page with react-hook-form and zod"
```

---

## Task 7: `ProtectedRoute` with redirect-on-401 test

**Files:**

- Create: `Gamefy/apps/web/src/components/shell/protected-route.tsx`
- Create: `Gamefy/apps/web/src/components/shell/protected-route.test.tsx`

- [ ] **Step 1: Write failing test**

Create `Gamefy/apps/web/src/components/shell/protected-route.test.tsx`:

```tsx
import { QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"

import { createQueryClient } from "@/lib/query-client"
import { ProtectedRoute } from "./protected-route"

function renderWithAuth(initial: string) {
  const client = createQueryClient()
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initial]}>
        <Routes>
          <Route path="/login" element={<div>login screen</div>} />
          <Route
            path="/inside"
            element={
              <ProtectedRoute>
                <div>protected content</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe("ProtectedRoute", () => {
  it("renders children when /api/auth/me succeeds", async () => {
    globalThis.fetch = vi.fn().mockResolvedValueOnce(
      new Response(
        JSON.stringify({ id: "u1", email: "x@y.z", role: "admin", is_active: true }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    )

    renderWithAuth("/inside")
    expect(await screen.findByText("protected content")).toBeInTheDocument()
  })

  it("redirects to /login when /api/auth/me returns 401", async () => {
    globalThis.fetch = vi.fn().mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Unauthorized" }), { status: 401 }),
    )

    renderWithAuth("/inside")
    await waitFor(() => expect(screen.getByText("login screen")).toBeInTheDocument())
  })

  it("renders a loading state while /api/auth/me is pending", () => {
    globalThis.fetch = vi.fn().mockImplementation(() => new Promise(() => {}))

    renderWithAuth("/inside")
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to confirm failure**

```powershell
bun run test src/components/shell/protected-route.test.tsx
```

Expected: 3 fails — module `./protected-route` not found.

- [ ] **Step 3: Implement `ProtectedRoute`**

Create `Gamefy/apps/web/src/components/shell/protected-route.tsx`:

```tsx
import type { ReactNode } from "react"
import { Navigate } from "react-router-dom"

import { useMe } from "@/lib/auth"

type ProtectedRouteProps = {
  children: ReactNode
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const me = useMe()

  if (me.isPending) {
    return (
      <div className="text-muted-foreground flex min-h-svh items-center justify-center text-sm">
        Loading…
      </div>
    )
  }

  if (me.isError || !me.data) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}
```

- [ ] **Step 4: Run tests**

```powershell
bun run test src/components/shell/protected-route.test.tsx
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

From `C:\Users\sarah\GamefyDB`:

```powershell
git add Gamefy/apps/web/src/components/shell/protected-route.tsx Gamefy/apps/web/src/components/shell/protected-route.test.tsx
git commit -m "feat(web): add ProtectedRoute that redirects to /login on 401"
```

---

## Task 8: `IconRail` + `TopBar` shell components

**Files:**

- Create: `Gamefy/apps/web/src/components/shell/icon-rail.tsx`
- Create: `Gamefy/apps/web/src/components/shell/top-bar.tsx`

(No new tests in this task — these components are pure layout; they're exercised by the smoke test in Task 11 and the manual browser pass.)

- [ ] **Step 1: Create `icon-rail.tsx`**

```tsx
import {
  BarChart3,
  Bot,
  Database,
  LineChart,
  Package,
  Settings,
  TrendingUp,
  Users,
} from "lucide-react"
import { NavLink } from "react-router-dom"

import { cn } from "@workspace/ui/lib/utils"

type Section = {
  to: string
  label: string
  icon: React.ComponentType<{ className?: string }>
}

const SECTIONS: Section[] = [
  { to: "/overview", label: "Overview", icon: BarChart3 },
  { to: "/transactions", label: "Transactions", icon: Database },
  { to: "/sessions", label: "Sessions", icon: LineChart },
  { to: "/stock", label: "Stock", icon: Package },
  { to: "/members", label: "Members", icon: Users },
  { to: "/forecasts", label: "Forecasts", icon: TrendingUp },
  { to: "/chat", label: "Chat", icon: Bot },
  { to: "/admin", label: "Admin", icon: Settings },
]

export function IconRail() {
  return (
    <nav
      aria-label="Sections"
      className="bg-card flex h-full w-14 flex-col items-center gap-1 border-r py-3"
    >
      {SECTIONS.map((section) => (
        <NavLink
          key={section.to}
          to={section.to}
          className={({ isActive }) =>
            cn(
              "text-muted-foreground hover:bg-muted hover:text-foreground inline-flex h-10 w-10 items-center justify-center rounded-md transition-colors",
              isActive && "bg-muted text-foreground",
            )
          }
          title={section.label}
        >
          <section.icon className="size-5" />
          <span className="sr-only">{section.label}</span>
        </NavLink>
      ))}
    </nav>
  )
}
```

- [ ] **Step 2: Create `top-bar.tsx`**

```tsx
import { LogOut } from "lucide-react"

import { Button } from "@workspace/ui/components/button"

import { useLogout, useMe } from "@/lib/auth"

export function TopBar() {
  const me = useMe()
  const logout = useLogout()

  return (
    <header className="bg-card flex h-12 items-center justify-between border-b px-4">
      <div className="font-semibold tracking-tight">GamefyDB</div>
      <div className="flex items-center gap-3 text-sm">
        {me.data ? (
          <span className="text-muted-foreground">
            {me.data.email} · <span className="uppercase">{me.data.role}</span>
          </span>
        ) : null}
        <Button
          variant="ghost"
          size="sm"
          onClick={() => logout.mutate()}
          disabled={logout.isPending}
        >
          <LogOut className="size-4" />
          Sign out
        </Button>
      </div>
    </header>
  )
}
```

- [ ] **Step 3: Typecheck**

From `C:\Users\sarah\GamefyDB\Gamefy\apps\web`:

```powershell
bun run typecheck
```

Expected: 0 errors.

- [ ] **Step 4: Commit**

From `C:\Users\sarah\GamefyDB`:

```powershell
git add Gamefy/apps/web/src/components/shell/icon-rail.tsx Gamefy/apps/web/src/components/shell/top-bar.tsx
git commit -m "feat(web): add icon-rail and top-bar shell components"
```

---

## Task 9: `AppShell` layout + placeholder pages

**Files:**

- Create: `Gamefy/apps/web/src/components/shell/app-shell.tsx`
- Create: `Gamefy/apps/web/src/pages/placeholders.tsx`

- [ ] **Step 1: Create `AppShell`**

Create `Gamefy/apps/web/src/components/shell/app-shell.tsx`:

```tsx
import { Outlet } from "react-router-dom"

import { IconRail } from "./icon-rail"
import { TopBar } from "./top-bar"

export function AppShell() {
  return (
    <div className="bg-background flex min-h-svh flex-col">
      <TopBar />
      <div className="flex flex-1">
        <IconRail />
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create placeholder pages**

Create `Gamefy/apps/web/src/pages/placeholders.tsx`:

```tsx
function Placeholder({ title, hint }: { title: string; hint: string }) {
  return (
    <div className="grid gap-2">
      <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
      <p className="text-muted-foreground text-sm">{hint}</p>
    </div>
  )
}

export function OverviewPage() {
  return <Placeholder title="Overview" hint="Charts arrive in Phase 4." />
}

export function TransactionsPage() {
  return <Placeholder title="Transactions" hint="Fact browser arrives in Phase 5." />
}

export function SessionsPage() {
  return <Placeholder title="Sessions" hint="Fact browser arrives in Phase 5." />
}

export function StockPage() {
  return <Placeholder title="Stock" hint="Dim browser arrives in Phase 5." />
}

export function MembersPage() {
  return <Placeholder title="Members" hint="Dim browser arrives in Phase 5." />
}

export function ForecastsPage() {
  return <Placeholder title="Forecasts" hint="Prophet / SARIMA / XGBoost arrive in Phase 7." />
}

export function ChatPage() {
  return <Placeholder title="Chat" hint="Gemini chatbot arrives in Phase 8." />
}

export function AdminPage() {
  return <Placeholder title="Admin" hint="Pipeline + users arrive in Phase 6 / 9." />
}
```

- [ ] **Step 3: Typecheck**

```powershell
bun run typecheck
```

Expected: 0 errors.

- [ ] **Step 4: Commit**

From `C:\Users\sarah\GamefyDB`:

```powershell
git add Gamefy/apps/web/src/components/shell/app-shell.tsx Gamefy/apps/web/src/pages/placeholders.tsx
git commit -m "feat(web): add AppShell layout and section placeholders"
```

---

## Task 10: Router + main entry

**Files:**

- Create: `Gamefy/apps/web/src/router.tsx`
- Modify: `Gamefy/apps/web/src/main.tsx`
- Delete: `Gamefy/apps/web/src/App.tsx`

- [ ] **Step 1: Create the route tree**

Create `Gamefy/apps/web/src/router.tsx`:

```tsx
import { createBrowserRouter, Navigate } from "react-router-dom"

import { AppShell } from "@/components/shell/app-shell"
import { ProtectedRoute } from "@/components/shell/protected-route"
import { LoginPage } from "@/pages/login"
import {
  AdminPage,
  ChatPage,
  ForecastsPage,
  MembersPage,
  OverviewPage,
  SessionsPage,
  StockPage,
  TransactionsPage,
} from "@/pages/placeholders"

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  {
    path: "/",
    element: (
      <ProtectedRoute>
        <AppShell />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <Navigate to="/overview" replace /> },
      { path: "overview", element: <OverviewPage /> },
      { path: "transactions", element: <TransactionsPage /> },
      { path: "sessions", element: <SessionsPage /> },
      { path: "stock", element: <StockPage /> },
      { path: "members", element: <MembersPage /> },
      { path: "forecasts", element: <ForecastsPage /> },
      { path: "chat", element: <ChatPage /> },
      { path: "admin", element: <AdminPage /> },
    ],
  },
  { path: "*", element: <Navigate to="/" replace /> },
])
```

- [ ] **Step 2: Rewrite `main.tsx`**

Replace `Gamefy/apps/web/src/main.tsx` with:

```tsx
import { QueryClientProvider } from "@tanstack/react-query"
import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { RouterProvider } from "react-router-dom"
import { Toaster } from "sonner"

import "@workspace/ui/globals.css"
import { ThemeProvider } from "@/components/theme-provider.tsx"
import { createQueryClient } from "@/lib/query-client"
import { router } from "@/router"

const queryClient = createQueryClient()

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
        <Toaster richColors closeButton />
      </QueryClientProvider>
    </ThemeProvider>
  </StrictMode>,
)
```

- [ ] **Step 3: Delete `App.tsx`**

From `C:\Users\sarah\GamefyDB\Gamefy\apps\web`:

```powershell
Remove-Item src/App.tsx
```

- [ ] **Step 4: Typecheck**

```powershell
bun run typecheck
```

Expected: 0 errors (the previous `App.tsx` import in `main.tsx` is gone, so this should be clean).

- [ ] **Step 5: Build**

```powershell
bun run build
```

Expected: succeeds; outputs `dist/` files. If it fails on a tailwind class warning, that's acceptable; on a TypeScript or import resolution error, fix before committing.

- [ ] **Step 6: Commit**

From `C:\Users\sarah\GamefyDB`:

```powershell
git add Gamefy/apps/web/src/router.tsx Gamefy/apps/web/src/main.tsx
git rm Gamefy/apps/web/src/App.tsx
git commit -m "feat(web): wire router with login, protected shell, and placeholders"
```

---

## Task 11: Smoke test + CLAUDE.md quickstart

**Files:**

- Modify: `CLAUDE.md` (local edit only — gitignored)

- [ ] **Step 1: Run the full test suite**

From `C:\Users\sarah\GamefyDB\Gamefy\apps\web`:

```powershell
bun run test
```

Expected: all Vitest tests passed — at least 14 (4 api + 4 auth + 3 login + 3 protected-route).

- [ ] **Step 2: Boot backend + frontend and walk through the demo**

In one PowerShell terminal (from `C:\Users\sarah\GamefyDB`):

```powershell
$env:GAMEFYDB_EXCEL_DIR = "C:/Users/sarah/GamefyDB/excel"
& C:/Users/sarah/AppData/Local/Python/bin/python -m uvicorn api.main:app --port 8000
```

In a second PowerShell terminal (from `C:\Users\sarah\GamefyDB\Gamefy\apps\web`):

```powershell
bun run dev
```

Then in a browser, open the URL printed by Vite (typically `http://localhost:5173`) and:

1. Confirm you land on `/login`.
2. Sign in with `admin@gamefy.com` + the seeded password.
3. Confirm you land on `/overview` inside the icon-rail shell.
4. Click each icon and confirm the placeholder page swaps.
5. Click **Sign out**, confirm you are bounced to `/login`.
6. Reload `http://localhost:5173/overview` directly — confirm you are redirected to `/login` (cookie cleared).
7. Sign in again and reload `http://localhost:5173/overview` — confirm the shell renders without bouncing.

If any of those steps fails, stop and report — do not commit a CLAUDE.md update describing a broken flow.

Stop both servers with Ctrl+C when done.

- [ ] **Step 3: Update `CLAUDE.md`** (local edit only — file is gitignored)

Append the following to `CLAUDE.md` after the existing API section:

```markdown
## Frontend (Phase 3+)

```powershell
# install workspace deps (once)
cd Gamefy
& bun install

# run the API on :8000 (from repo root)
cd C:/Users/sarah/GamefyDB
$env:GAMEFYDB_EXCEL_DIR = "C:/Users/sarah/GamefyDB/excel"
& C:/Users/sarah/AppData/Local/Python/bin/python -m uvicorn api.main:app --port 8000

# run the SPA on :5173 (proxies /api → :8000)
cd Gamefy/apps/web
& bun run dev
```

Open `http://localhost:5173/login` and sign in. Route guard (`<ProtectedRoute>`)
calls `GET /api/auth/me`; on 401 it redirects to `/login`. Auth state lives in
TanStack Query under the `["auth", "me"]` key — invalidated on login/logout.

Frontend tests (Vitest + RTL):

```powershell
cd Gamefy/apps/web
& bun run test
```
```

- [ ] **Step 4: Final git status check**

From `C:\Users\sarah\GamefyDB`:

```powershell
git status
git log --oneline -15
```

Expected: clean working tree (`CLAUDE.md` remains gitignored, `Gamefy/node_modules` ignored). 10 new commits for Phase 3 on top of the Phase 2 head.

- [ ] **Step 5: Report Phase 3 summary**

No commit in this step. Report to the user:

- Vitest count (final summary line)
- Commit log for Phase 3
- Confirmation that the manual login flow succeeded
- Confirmation that `bun run build` and `bun run typecheck` were both clean
- CLAUDE.md updated locally (not committed)
- Any deviations from the plan and why
