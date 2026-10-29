export type ApplicationEnvironment = "development" | "production"
export type AuthenticationMode = "development" | "session"

function positiveNumber(value: string | undefined, fallback: number): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback
}

const name: ApplicationEnvironment = import.meta.env.VITE_APP_ENV
  ?? (import.meta.env.PROD ? "production" : "development")
const developmentFeatures = name === "development" && !import.meta.env.PROD
const authMode: AuthenticationMode = developmentFeatures && import.meta.env.VITE_AUTH_MODE !== "session"
  ? "development"
  : "session"

export const environment = {
  name,
  isDevelopment: developmentFeatures,
  authMode,
  apiBaseUrl: (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, ""),
  apiTimeoutMs: positiveNumber(import.meta.env.VITE_API_TIMEOUT_MS, 5000),
} as const
