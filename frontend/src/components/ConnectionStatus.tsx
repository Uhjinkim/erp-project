import type { SystemHealth } from "../types/health"

type ConnectionStatusProps = {
  health: SystemHealth | null
  checking: boolean
  message: string
  simulatedOffline: boolean
  showDevelopmentControls: boolean
  onCheck: () => void
  onToggleOffline: () => void
}

const statusLabels: Record<string, string> = {
  connected: "연결됨",
  disconnected: "미연결",
  not_configured: "미설정",
  offline_simulation: "오프라인",
  development_simulation: "개발 대역",
}

function statusClass(status: string): string {
  return status === "connected" || status === "development_simulation" ? "connected" : "disconnected"
}

export function ConnectionStatus({
  health,
  checking,
  message,
  simulatedOffline,
  showDevelopmentControls,
  onCheck,
  onToggleOffline,
}: ConnectionStatusProps) {
  const backendStatus = simulatedOffline ? "offline_simulation" : health?.services.backend.status ?? "disconnected"
  const databaseStatus = simulatedOffline ? "offline_simulation" : health?.services.database.status ?? "disconnected"
  const redisStatus = simulatedOffline ? "offline_simulation" : health?.services.redis.status ?? "disconnected"
  const workforceStatus = simulatedOffline ? "offline_simulation" : health?.services.workforce.status ?? "disconnected"
  const endToEndStatus = simulatedOffline ? "disconnected" : health?.end_to_end.status ?? "disconnected"

  const items = [
    ["백엔드", backendStatus],
    ["PostgreSQL", databaseStatus],
    ["Redis", redisStatus],
    ["사원 연동", workforceStatus],
    ["End to end", endToEndStatus],
  ]

  return (
    <section className="connection-panel" aria-label="서비스 연결 상태">
      <div className="connection-summary">
        <div>
          <p className="eyebrow">CONNECTION</p>
          <strong>{endToEndStatus === "connected" ? "온라인" : "오프라인 / 미연결"}</strong>
          {message && <p className="connection-message">{message}</p>}
        </div>
        <div className="connection-controls">
          {showDevelopmentControls && (
            <button type="button" onClick={onToggleOffline}>
              {simulatedOffline ? "실제 연결 확인" : "오프라인 테스트"}
            </button>
          )}
          <button type="button" onClick={onCheck} disabled={checking || simulatedOffline}>
            {checking ? "확인 중" : "연결 확인"}
          </button>
        </div>
      </div>
      <ul className="connection-list">
        {items.map(([label, status]) => (
          <li key={label}>
            <span>{label}</span>
            <b className={`connection-badge connection-badge--${statusClass(status)}`}>
              {statusLabels[status] ?? status}
            </b>
          </li>
        ))}
      </ul>
    </section>
  )
}
