import { environment } from "../config/environment"

export class ApiError extends Error {
  constructor(
    message: string,
    readonly unavailable: boolean,
    readonly status?: number,
    readonly fieldErrors: Record<string, string[]> = {},
  ) {
    super(message)
    this.name = "ApiError"
  }
}

const accessFailureListeners = new Set<() => void>()
export function subscribeAccessFailure(listener: () => void) {
  accessFailureListeners.add(listener)
  return () => { accessFailureListeners.delete(listener) }
}

function fieldErrors(body: unknown): Record<string, string[]> {
  if (!body || typeof body !== "object") return {}
  return Object.fromEntries(Object.entries(body).flatMap(([key, value]) =>
    key !== "detail" && Array.isArray(value)
      ? [[key, value.filter((item): item is string => typeof item === "string")]]
      : []))
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

// DRF는 업무 오류를 {"detail": "..."}로, 입력 검증 오류를 {"field": ["..."]}로 반환한다.
function errorDetail(body: unknown): string | undefined {
  if (!body || typeof body !== "object") return undefined
  if ("detail" in body && typeof body.detail === "string") return body.detail
  for (const value of Object.values(body)) {
    const message = Array.isArray(value) ? value.find((item) => typeof item === "string") : value
    if (typeof message === "string") return message
  }
  return undefined
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
      if ((response.status === 401 || response.status === 403) && !path.startsWith("/api/auth/")) {
        accessFailureListeners.forEach((listener) => listener())
      }
      throw new ApiError(errorDetail(body) ?? "요청을 처리하지 못했습니다.", response.status >= 500, response.status, fieldErrors(body))
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
