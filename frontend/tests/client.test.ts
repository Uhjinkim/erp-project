import { afterAll, beforeEach, describe, expect, mock, test } from "bun:test"

mock.module("../src/config/environment", () => ({ environment: { apiBaseUrl: "", apiTimeoutMs: 1000 } }))
const { requestJson, ApiError, subscribeAccessFailure } = await import("../src/api/client")
const previousFetch = globalThis.fetch
const previousWindow = Object.getOwnPropertyDescriptor(globalThis, "window")
const previousDocument = Object.getOwnPropertyDescriptor(globalThis, "document")
Object.defineProperty(globalThis, "window", { configurable: true, value: { setTimeout, clearTimeout } })
Object.defineProperty(globalThis, "document", { configurable: true, value: { cookie: "csrftoken=synthetic%20token" } })
afterAll(() => {
  globalThis.fetch = previousFetch
  if (previousWindow) Object.defineProperty(globalThis, "window", previousWindow)
  else Reflect.deleteProperty(globalThis, "window")
  if (previousDocument) Object.defineProperty(globalThis, "document", previousDocument)
  else Reflect.deleteProperty(globalThis, "document")
})
let calls: { path: string; options: RequestInit }[] = []
beforeEach(() => { calls = [] })
function respond(status: number, body?: unknown) {
  globalThis.fetch = mock(async (input: RequestInfo | URL, options?: RequestInit) => {
    calls.push({ path: String(input), options: options ?? {} })
    return new Response(body === undefined ? null : JSON.stringify(body), { status })
  }) as unknown as typeof fetch
}
describe("shared API transport", () => {
  test("writes keep session cookies and decoded CSRF; 204 accepts an empty body", async () => {
    respond(204)
    expect(await requestJson("/api/example/", { method: "POST" })).toBeNull()
    expect(calls[0].options.credentials).toBe("same-origin")
    expect(new Headers(calls[0].options.headers).get("X-CSRFToken")).toBe("synthetic token")
  })
  test("field errors keep their keys for form feedback", async () => {
    respond(400, { use_days: ["invalid", 42], start_datetime: ["required"] })
    const error = await requestJson("/api/example/").catch((failure) => failure)
    expect(error).toBeInstanceOf(ApiError)
    expect(error.fieldErrors).toEqual({ use_days: ["invalid"], start_datetime: ["required"] })
    expect(error.unavailable).toBe(false)
  })
  test("business 403 asks for session verification without recursing on auth 403", async () => {
    const listener = mock(() => {})
    const unsubscribe = subscribeAccessFailure(listener)
    respond(403, { detail: "forbidden" })
    await requestJson("/api/workforce/employees/").catch(() => {})
    expect(listener).toHaveBeenCalledTimes(1)
    await requestJson("/api/auth/me/").catch(() => {})
    expect(listener).toHaveBeenCalledTimes(1)
    unsubscribe()
    await requestJson("/api/board/posts/").catch(() => {})
    expect(listener).toHaveBeenCalledTimes(1)
  })
  test("service failures retain availability information", async () => {
    respond(503, { detail: "unavailable" })
    const error = await requestJson("/api/example/").catch((failure) => failure)
    expect(error.status).toBe(503)
    expect(error.unavailable).toBe(true)
    globalThis.fetch = mock(async () => { throw new TypeError("offline") }) as unknown as typeof fetch
    await expect(requestJson("/api/example/")).rejects.toMatchObject({ unavailable: true })
  })
})
