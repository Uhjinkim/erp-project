import type { Route } from "./routing"
import type { CurrentUser } from "../types/auth"
import { VacationPanel } from "../features/vacation"
import { BoardScreen } from "../features/board"
import { WorkforceScreen } from "../features/workforce"
import { EvaluationModule } from "../features/evaluation"
import { PayrollScreen } from "../features/payroll"
import { ProfileScreen } from "../features/profile"
import { EmptyState } from "../components/ui"

export function ModuleScreen({ route, user }: { route: Route; user: CurrentUser | null }) {
  if (route.moduleId === "vacation") return <VacationPanel currentUser={user} screenId={route.screenId} search={route.search} />
  if (route.screenId === "home" || route.screenId === "manager-home") return <EmptyState title="업무 홈을 준비하고 있습니다" />
  const implemented = ["board", "evaluation", "payroll", "workforce", "profile"].includes(route.moduleId)
  if (!implemented) return <EmptyState title="화면을 준비하고 있습니다" />
  if (!user) return <EmptyState title="세션 로그인이 필요한 업무입니다" />
  if (route.moduleId === "profile") return <ProfileScreen route={route} user={user} enabled />
  if (route.moduleId === "board") return <BoardScreen route={route} enabled />
  if (route.moduleId === "evaluation") return <EvaluationModule route={route} user={user} enabled />
  if (route.moduleId === "payroll") return <PayrollScreen route={route} currentUser={user} enabled />
  if (route.moduleId === "workforce") return <WorkforceScreen route={route} currentUser={user} enabled />
  return <EmptyState title="화면을 준비하고 있습니다" />
}
