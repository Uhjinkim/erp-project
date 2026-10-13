import { requestJson } from "./client"
import { environment } from "../config/environment"

export function requestVacation<T>(path: string, employeeNo: number, options: RequestInit = {}) {
  const headers = new Headers(options.headers)
  headers.set("Content-Type", "application/json")
  if (environment.authMode === "development") headers.set("X-Employee-No", String(employeeNo))
  return requestJson<T>(`/api/vacations/${path}`, { ...options, headers })
}
