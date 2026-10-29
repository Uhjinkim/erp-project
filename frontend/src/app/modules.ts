import type { ModuleRegistration } from "./routing"
import type { CurrentUser } from "../types/auth"
import { registration as profile } from "../features/profile/registration"
import { registration as workforce } from "../features/workforce/registration"
import { registration as vacation } from "../features/vacation/registration"
import { registration as board } from "../features/board/registration"
import { registration as evaluation } from "../features/evaluation/registration"
import { registration as payroll } from "../features/payroll/registration"
import { isPayrollManager } from "../features/payroll/model"

// 배포 범위에 포함된 업무만 등록한다. 홈·계정 관리는 구현 후 연결한다.
export const modules: ModuleRegistration[] = [profile, workforce, vacation, board, evaluation, payroll]

export function visibleModules(user: CurrentUser | null) {
  const hr = user?.roles.includes("HR_MANAGER") ?? false
  const payrollManager = user ? isPayrollManager(user) : false
  const head = user?.is_department_head ?? false
  const profileProcessor = hr || user?.is_superuser
  const leaveApprover = head || user?.roles.includes("HR_LEAVE_APPROVER")
  return modules.filter((module) => !module.requiredRole || user?.roles.includes(module.requiredRole) || (module.allowSuperuser && user?.is_superuser))
    .map((module) => {
      const screens = module.screens.filter((screen) => {
        if (module.id === "payroll" && screen.id !== "payslip") return payrollManager
        if (module.id === "evaluation" && screen.id === "evaluation-hr") return hr
        if (module.id === "profile" && ["change-queue", "change-review"].includes(screen.id)) return profileProcessor
        return true
      }).map((screen) => {
        // 상세·처리는 목록에서 대상을 선택한다. 이전 담당자도 직접 링크로 진입할 수 있다.
        const contextual = ["change-review", "evaluation-form", "leave-detail", "leave-approve", "leave-recall", "leave-resubmit"].includes(screen.id)
        const hidden = contextual || (screen.id === "evaluation-team" && !head) || (screen.id === "leave-queue" && !leaveApprover)
        return hidden ? { ...screen, menu: false } : screen
      })
      const entry = module.id === "evaluation" ? head ? "evaluation-team" : hr ? "evaluation-hr" : "evaluation-mine" : module.entry
      return { ...module, screens, entry }
    })
}
