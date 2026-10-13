import type { SystemHealth } from "../types/health"
import { Badge, Button, Card, DetailList } from "./ui"

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
  connected: "연결됨", disconnected: "미연결", not_configured: "미설정",
  offline_simulation: "오프라인", development_simulation: "개발 대역",
}
export function ConnectionStatus({ health, checking, message, simulatedOffline, showDevelopmentControls, onCheck, onToggleOffline }: ConnectionStatusProps) {
  const items: [string, string | undefined][] = [
    ["백엔드", health?.services.backend.status], ["데이터베이스", health?.services.database.status],
    ["캐시", health?.services.redis.status], ["사원 연동", health?.services.workforce.status],
    ["전체 연결", health?.end_to_end.status],
  ]
  return <Card title="서비스 연결 상태" actions={<Button size="small" variant="secondary" onClick={onCheck} pending={checking} disabled={simulatedOffline}>연결 확인</Button>}>
    {message && <p>{message}</p>}
    <DetailList items={items.map(([label, rawStatus]) => {
      const status = simulatedOffline ? "offline_simulation" : rawStatus ?? "disconnected"
      return { key: label, label, value: <Badge tone={status === "connected" || status === "development_simulation" ? "success" : "warning"}>{statusLabels[status] ?? "미확인"}</Badge> }
    })} />
    {showDevelopmentControls && <Button size="small" variant="ghost" onClick={onToggleOffline}>{simulatedOffline ? "실제 연결 확인" : "오프라인 테스트"}</Button>}
  </Card>
}
