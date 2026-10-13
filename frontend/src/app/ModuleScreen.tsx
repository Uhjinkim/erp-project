import type { Route } from "./routing"
import type { useConnection } from "./useConnection"
import type { CurrentUser } from "../types/auth"
import { VacationPanel } from "../features/vacation"
import { BoardScreen } from "../features/board"
import { WorkforcePanel } from "../features/workforce"
import { EvaluationPanel } from "../features/evaluation"
import { PayrollPanel } from "../features/payroll"
import { ProfileScreen } from "../features/profile"
import { ConnectionStatus } from "../components/ConnectionStatus"
import { EmptyState } from "../components/ui"
import { environment } from "../config/environment"

export function ModuleScreen({ route, user, connection }: { route: Route; user: CurrentUser | null; connection: ReturnType<typeof useConnection> }) {
  if (route.screenId === "leave-apply") return <VacationPanel currentUser={user} connected={connection.vacationConnected} />
  if (route.screenId === "system-health") return <ConnectionStatus health={connection.health} checking={connection.checking} message={connection.message} simulatedOffline={connection.simulatedOffline} showDevelopmentControls={environment.connectionTestControls} onCheck={() => void connection.check()} onToggleOffline={connection.toggleOffline} />
  if (route.screenId === "home" || route.screenId === "manager-home") return <EmptyState title="업무 홈을 준비하고 있습니다">홈 카드와 집계 API는 기능 담당자가 연결합니다. 왼쪽 메뉴에서 현재 업무 화면을 이용하세요.</EmptyState>
  const implemented = ["board-list", "board-write","employee-list", "evaluation-team", "payroll-periods", "my-profile"]
  if (!implemented.includes(route.screenId)) return <EmptyState title="화면을 준비하고 있습니다">공통 토대와 화면 주소가 등록되었습니다. 상세 업무 화면은 모듈별 작업에서 구현합니다.</EmptyState>
  if (!user) return <EmptyState title="세션 로그인이 필요한 업무입니다">개발용 사원 식별은 휴가에서만 사용할 수 있습니다. 세션 인증 모드로 실행해 로그인하세요.</EmptyState>
  if (route.screenId === "my-profile") return <ProfileScreen user={user} enabled={connection.backendConnected} />
  if (route.moduleId === "board") return <BoardScreen route={route} enabled={connection.backendConnected} />
  const props = { currentUser: user, enabled: connection.backendConnected }
  return <div className="legacy-module">
    {route.screenId === "employee-list" && <WorkforcePanel {...props} />}
    {route.screenId === "evaluation-team" && <EvaluationPanel {...props} />}
    {route.screenId === "payroll-periods" && <PayrollPanel {...props} />}
  </div>
}
