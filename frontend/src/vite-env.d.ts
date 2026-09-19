/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_APP_ENV?: "development" | "production"
  readonly VITE_AUTH_MODE?: "development" | "session"
  readonly VITE_API_BASE_URL?: string
  readonly VITE_API_TIMEOUT_MS?: string
  readonly VITE_HEALTH_POLL_INTERVAL_MS?: string
  readonly VITE_ENABLE_CONNECTION_TEST_CONTROLS?: string
  readonly VITE_DEV_OFFLINE_MODE?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
