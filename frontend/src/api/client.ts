import { environment } from "../config/environment"

export class ApiError extends Error {
  constructor(
    message: string,
    readonly unavailable: boolean,
    readonly status?: number,
  ) {
    super(message)
    this.name = "ApiError"
  }
}

function csrfToken(): string | undefined {
  return document.cookie
    .split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith("csrftoken="))
    ?.split("=")
    .slice(1)
    .join("=")
}

export async function requestJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), environment.apiTimeoutMs)
  const headers = new Headers(options.headers)
  const method = (options.method ?? "GET").toUpperCase()
  const token = csrfToken()
  if (!["GET", "HEAD", "OPTIONS", "TRACE"].includes(method) && token) {
    headers.set("X-CSRFToken", decodeURIComponent(token))
  }

  try {
    const response = await fetch(`${environment.apiBaseUrl}${path}`, {
      ...options,
      credentials: "same-origin",
      headers,
      signal: controller.signal,
    })
    const body = await response.json().catch(() => null) as { detail?: string } | T | null

    if (!response.ok) {
      const detail = body && typeof body === "object" && "detail" in body ? body.detail : undefined
      throw new ApiError(detail ?? "요청을 처리하지 못했습니다.", response.status >= 500, response.status)
    }

    return body as T
  } catch (error) {
    if (error instanceof ApiError) throw error
    const timedOut = error instanceof DOMException && error.name === "AbortError"
    throw new ApiError(
      timedOut ? "서버 응답 시간이 초과되었습니다." : "백엔드 서버에 연결할 수 없습니다.",
      true,
    )
  } finally {
    window.clearTimeout(timeout)
  }
}
