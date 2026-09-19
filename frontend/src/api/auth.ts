import { requestJson } from "./client"
import type { CurrentUser } from "../types/auth"

export async function getCurrentUser(): Promise<CurrentUser> {
  return requestJson<CurrentUser>("/api/auth/me/")
}

export async function loginWithEmail(email: string, password: string): Promise<CurrentUser> {
  await requestJson<{ detail: string }>("/api/auth/csrf/")
  return requestJson<CurrentUser>("/api/auth/login/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  })
}

export async function logoutSession(): Promise<void> {
  await requestJson<null>("/api/auth/logout/", { method: "POST" })
}
