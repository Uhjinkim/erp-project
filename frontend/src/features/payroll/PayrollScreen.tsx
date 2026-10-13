import type { Route } from "../../app/routing"
import { routeHref } from "../../app/routing"
import { EmptyState } from "../../components/ui"
import type { CurrentUser } from "../../types/auth"
import { isPayrollManager } from "./model"
import { ConfirmScreen } from "./screens/ConfirmScreen"
import { CreateScreen } from "./screens/CreateScreen"
import { ItemsScreen } from "./screens/ItemsScreen"
import { PayslipScreen } from "./screens/PayslipScreen"
import { PeriodsScreen } from "./screens/PeriodsScreen"

type PayrollScreenProps = {
  route: Route
  currentUser: CurrentUser
  enabled: boolean
}

// Query keys: period=YYYY-MM (create/item/confirm), statementId (item).
export function PayrollScreen({ route, currentUser, enabled }: PayrollScreenProps) {
  if (!enabled) return <EmptyState title="백엔드 연결 후 급여 정보를 불러옵니다" />
  if (route.screenId === "payslip") {
    if (!currentUser.employee) return <EmptyState title="연결된 사원 정보가 없습니다">관리자에게 계정과 사원 연결을 문의하세요.</EmptyState>
    return <PayslipScreen enabled={enabled} />
  }
  // Display gate only; the payroll API enforces PAYROLL_MANAGER on every manager endpoint.
  if (!isPayrollManager(currentUser)) {
    return (
      <EmptyState
        title="급여담당자 전용 화면입니다"
        action={<a href={routeHref({ moduleId: "payroll", screenId: "payslip" })}>내 급여명세로 이동</a>}
      >
        본인 급여명세는 &lsquo;내 급여명세&rsquo;에서 볼 수 있습니다.
      </EmptyState>
    )
  }
  const search = new URLSearchParams(route.search ?? "")
  const shared = { enabled, ownEmployeeNo: currentUser.employee?.emp_no ?? null, search }
  // Keyed by query so following a link to the same screen resets its filters.
  const key = route.search ?? ""
  if (route.screenId === "payroll-periods") return <PeriodsScreen enabled={enabled} />
  if (route.screenId === "payroll-create") return <CreateScreen key={key} {...shared} />
  if (route.screenId === "payroll-item") return <ItemsScreen key={key} {...shared} />
  if (route.screenId === "payroll-confirm") return <ConfirmScreen key={key} {...shared} />
  return <EmptyState title="등록되지 않은 급여 화면입니다" />
}
