import type { Route } from "../../app/routing"
import { routeHref } from "../../app/routing"
import { EmptyState } from "../../components/ui"
import type { CurrentUser } from "../../types/auth"
import { QueryFallback } from "./components/QueryFallback"
import { useMasterData } from "./hooks"
import { isHRManager } from "./model"
import { EmployeeCreateScreen } from "./screens/EmployeeCreateScreen"
import { EmployeeDetailScreen } from "./screens/EmployeeDetailScreen"
import { EmployeeListScreen } from "./screens/EmployeeListScreen"
import { OrgScreen } from "./screens/OrgScreen"
import { RehireScreen } from "./screens/RehireScreen"
import { RetireScreen } from "./screens/RetireScreen"
import { RoleGrantScreen } from "./screens/RoleGrantScreen"

type WorkforceScreenProps = {
  route: Route
  currentUser: CurrentUser
  enabled: boolean
}

const hrOnlyScreens = ["employee-list", "employee-detail", "employee-create", "retire", "rehire", "role-grant"]

export function WorkforceScreen({ route, currentUser, enabled }: WorkforceScreenProps) {
  // 부서·직급·역할은 인증 사용자 모두 조회할 수 있으며 화면 이동 사이에 유지한다.
  const master = useMasterData(enabled)
  if (!enabled) return <EmptyState title="백엔드 연결 후 사원·조직 정보를 불러옵니다" />
  const manager = isHRManager(currentUser)
  // 화면 안내용 판정이다. 직접 URL로 들어와도 workforce API가 HR-001·HR-005 권한을 다시 검사한다.
  if (hrOnlyScreens.includes(route.screenId) && !manager) {
    return (
      <EmptyState
        title="인사관리자 전용 화면입니다"
        action={<a href={routeHref({ moduleId: "profile", screenId: "my-profile" })}>내 인사정보로 이동</a>}
      >
        본인 인사정보는 &lsquo;내 인사정보&rsquo;에서 확인할 수 있습니다. 부서·직급은 &lsquo;부서·직급 관리&rsquo;에서 조회할 수 있습니다.
      </EmptyState>
    )
  }
  if (!master.data) return <QueryFallback query={master} label="부서·직급 정보를 불러오는 중" />
  const search = new URLSearchParams(route.search ?? "")
  const shared = { enabled, search, master: master.data }
  // 조회 조건이 바뀌면 화면을 다시 마운트해 필터·입력 상태를 URL과 맞춘다.
  const key = `${route.screenId}?${route.search ?? ""}`
  switch (route.screenId) {
    case "employee-list": return <EmployeeListScreen key={key} {...shared} />
    case "employee-detail": return <EmployeeDetailScreen key={key} {...shared} />
    case "employee-create": return <EmployeeCreateScreen key={key} master={master.data} />
    case "retire": return <RetireScreen key={key} {...shared} />
    case "rehire": return <RehireScreen key={key} {...shared} />
    case "role-grant": return <RoleGrantScreen key={key} {...shared} />
    case "org": return <OrgScreen key={key} {...shared} canEdit={manager} onChanged={() => void master.reload()} />
    default: return <EmptyState title="등록되지 않은 사원·조직 화면입니다" />
  }
}
