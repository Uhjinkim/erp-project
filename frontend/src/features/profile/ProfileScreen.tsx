import { useCallback } from "react"
import { getMyEmployeeInfo, listChangeRequests } from "../../api/profile"
import type { Route } from "../../app/routing"
import { EmptyState } from "../../components/ui"
import type { CurrentUser } from "../../types/auth"
import { QueryFallback } from "./components/QueryFallback"
import { useProfileQuery } from "./hooks"
import { ChangeHistoryScreen } from "./screens/ChangeHistoryScreen"
import { ChangeQueueScreen } from "./screens/ChangeQueueScreen"
import { ChangeReviewScreen } from "./screens/ChangeReviewScreen"
import { MyProfileScreen } from "./screens/MyProfileScreen"

const selfScreens = ["my-profile", "change-history"]

type ProfileScreenProps = { route: Route; user: CurrentUser; enabled: boolean }

export function ProfileScreen({ route, user, enabled }: ProfileScreenProps) {
  const search = new URLSearchParams(route.search ?? "")
  // 조회 조건이 바뀌면 화면을 다시 마운트해 필터·입력 상태를 URL과 맞춘다.
  const key = `${route.screenId}?${route.search ?? ""}`
  if (!enabled) return <EmptyState title="백엔드 연결 후 개인정보를 불러옵니다" />
  // 처리함은 인사관리자뿐 아니라 HR 요청의 처리자로 지정된 부서장·superuser도 사용한다. 대상은 서버가 거른다.
  if (route.screenId === "change-queue") return <ChangeQueueScreen key={key} enabled={enabled} search={search} />
  if (route.screenId === "change-review") return <ChangeReviewScreen key={key} enabled={enabled} search={search} />
  if (!selfScreens.includes(route.screenId)) return <EmptyState title="등록되지 않은 내 정보 화면입니다" />
  if (!user.employee) return <EmptyState title="연결된 사원 정보가 없습니다">관리자에게 계정과 사원 연결을 문의하세요.</EmptyState>
  return <SelfService routeKey={key} screenId={route.screenId} search={search} enabled={enabled} />
}

// 대기 요청이 없을 때(null)와 아직 조회 전을 구분하기 위해 객체로 감싼다.
const loadPending = async () => ({ request: (await listChangeRequests({ mine: true, status: "대기" }))[0] ?? null })

// 본인 정보와 대기 요청은 화면 이동 사이에 유지하고, 수정 요청 제출·취소 후 다시 조회한다.
function SelfService({ routeKey, screenId, search, enabled }: { routeKey: string; screenId: string; search: URLSearchParams; enabled: boolean }) {
  const loadEmployee = useCallback(() => getMyEmployeeInfo(), [])
  const employee = useProfileQuery(enabled, loadEmployee)
  const pending = useProfileQuery(enabled, loadPending)
  if (screenId === "change-history") {
    return <ChangeHistoryScreen key={routeKey} enabled={enabled} search={search} onChanged={() => void pending.reload()} />
  }
  if (!employee.data) return <QueryFallback query={employee} label="본인 정보를 불러오는 중" notFoundTitle="연결된 사원 정보가 없습니다" />
  // 대기 요청 조회가 실패해도 본인 정보는 표시한다. 요청 제한은 서버가 다시 확인한다.
  const pendingRequest = pending.data?.request ?? null
  return <MyProfileScreen key={routeKey} employee={employee.data} pending={pendingRequest} search={search} onSubmitted={() => void pending.reload()} />
}
