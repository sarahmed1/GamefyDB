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
