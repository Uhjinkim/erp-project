import type { CurrentUser } from "../../types/auth"
import type { PayrollItem, PayrollStatement, PayrollStatus, PayrollTargetEmployee } from "../../types/payroll"

export type AmountValues = Record<string, string>
export type Department = { key: string; name: string }
export type PeriodSummary = { period: string; drafts: number; confirmed: number; missing: number }

// Select value for employees without a department.
export const NO_DEPARTMENT = "none"

export function isPayrollManager(user: CurrentUser): boolean {
  return user.is_superuser || user.roles.includes("PAYROLL_MANAGER")
}

export function currentPeriod(now = new Date()): string {
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`
}

export function periodKey(statement: Pick<PayrollStatement, "year" | "month">): string {
  return `${statement.year}-${String(statement.month).padStart(2, "0")}`
}

export function previousPeriod(period: string): string {
  const [year, month] = period.split("-").map(Number)
  return month === 1 ? `${year - 1}-12` : `${year}-${String(month - 1).padStart(2, "0")}`
}

export function statementFor(statements: PayrollStatement[], empNo: string, period: string): PayrollStatement | null {
  return statements.find((item) => String(item.employee_no) === empNo && periodKey(item) === period) ?? null
}

export function periodLabel(period: string): string {
  const [year, month] = period.split("-")
  return `${year}년 ${Number(month)}월`
}

export function isPeriod(value: string | null): value is string {
  return value !== null && /^\d{4}-(0[1-9]|1[0-2])$/.test(value)
}

export function won(value: number): string {
  return `${Math.trunc(value).toLocaleString("ko-KR")}원`
}

export function statusTone(status: PayrollStatus): "success" | "warning" {
  return status === "확정" ? "success" : "warning"
}

export function amountValuesFromItems(items: PayrollItem[]): AmountValues {
  return Object.fromEntries(items.map((item) => [item.component_code, String(Math.trunc(item.amount))]))
}

export function itemsFromAmountValues(values: AmountValues): Pick<PayrollItem, "component_code" | "amount">[] {
  return Object.entries(values)
    .filter(([, amount]) => amount.trim() !== "")
    .map(([component_code, amount]) => ({ component_code, amount: Math.trunc(Number(amount)) }))
}

export function departmentKey(employee: Pick<PayrollTargetEmployee, "dept_no">): string {
  return employee.dept_no === null ? NO_DEPARTMENT : String(employee.dept_no)
}

export function departmentsOf(targets: PayrollTargetEmployee[]): Department[] {
  const byKey = new Map<string, Department>()
  for (const employee of targets) {
    const key = departmentKey(employee)
    if (!byKey.has(key)) byKey.set(key, { key, name: employee.dept_name ?? (employee.dept_no === null ? "부서 미지정" : key) })
  }
  return [...byKey.values()].sort((left, right) =>
    left.key === NO_DEPARTMENT ? 1 : right.key === NO_DEPARTMENT ? -1 : left.name.localeCompare(right.name, "ko"))
}

export function employeesIn(targets: PayrollTargetEmployee[], deptKey: string): PayrollTargetEmployee[] {
  return deptKey ? targets.filter((employee) => departmentKey(employee) === deptKey) : targets
}

// Active employees with no statement for the period. "Active" is today's status, not the period's.
export function missingEmployees(
  targets: PayrollTargetEmployee[],
  statements: PayrollStatement[],
  period: string,
): PayrollTargetEmployee[] {
  const written = new Set(statements.filter((item) => periodKey(item) === period).map((item) => item.employee_no))
  return targets.filter((employee) => employee.is_active && !written.has(employee.emp_no))
}

// Newest first; the current period is always listed so a new month can be started.
export function summarizePeriods(
  targets: PayrollTargetEmployee[],
  statements: PayrollStatement[],
  current: string,
): PeriodSummary[] {
  const periods = new Set([current, ...statements.map(periodKey)])
  return [...periods]
    .sort((left, right) => right.localeCompare(left))
    .map((period) => {
      const inPeriod = statements.filter((item) => periodKey(item) === period)
      return {
        period,
        drafts: inPeriod.filter((item) => item.status === "작성중").length,
        confirmed: inPeriod.filter((item) => item.status === "확정").length,
        missing: missingEmployees(targets, statements, period).length,
      }
    })
}
