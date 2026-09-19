export type ServiceConnectionStatus =
  | "connected"
  | "disconnected"
  | "not_configured"
  | "offline_simulation"
  | "development_simulation"

export type ServiceHealth = {
  status: ServiceConnectionStatus
  detail?: string
}

export type SystemHealth = {
  status: "online" | "degraded" | "offline"
  environment: "development" | "production" | "test"
  services: {
    backend: ServiceHealth
    database: ServiceHealth
    redis: ServiceHealth
    workforce: ServiceHealth
  }
  end_to_end: ServiceHealth
}
