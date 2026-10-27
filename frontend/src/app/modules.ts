import type { ModuleRegistration } from "./routing"
import type { CurrentUser } from "../types/auth"
import { registration as home } from "../features/home/registration"
import { registration as profile } from "../features/profile/registration"
import { registration as workforce } from "../features/workforce/registration"
import { registration as vacation } from "../features/vacation/registration"
import { registration as board } from "../features/board/registration"
import { registration as evaluation } from "../features/evaluation/registration"
import { registration as payroll } from "../features/payroll/registration"
import { registration as system } from "../features/system/registration"

export const modules: ModuleRegistration[] = [home, profile, workforce, vacation, board, evaluation, payroll, system]

export function visibleModules(user: CurrentUser | null) {
  return modules.filter((module) => !module.requiredRole || (user?.roles.includes(module.requiredRole) ?? false))
}
