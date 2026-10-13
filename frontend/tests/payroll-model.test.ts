import { describe, expect, test } from "bun:test"
import {
  NO_DEPARTMENT,
  departmentsOf,
  employeesIn,
  isPeriod,
  itemsFromAmountValues,
  missingEmployees,
  previousPeriod,
  statementFor,
  summarizePeriods,
} from "../src/features/payroll/model"
import type { PayrollStatement, PayrollTargetEmployee } from "../src/types/payroll"

const target = (emp_no: number, dept_no: number | null, is_active = true): PayrollTargetEmployee => ({
  emp_no, name: `사원${emp_no}`, dept_no, dept_name: dept_no === null ? null : `부서${dept_no}`, position_name: null, is_active,
})

const statement = (statement_id: number, employee_no: number, month: number, status: "작성중" | "확정"): PayrollStatement => ({
  statement_id, employee_no, employee: { emp_no: employee_no, name: null, position_name: null }, year: 2026, month,
  payment_date: "2026-01-23", status, items: [], total_earnings: 0, total_deductions: 0, net_pay: 0,
  confirmed_by: null, confirmed_at: null,
})

const targets = [target(1, 10), target(2, 10), target(3, null), target(4, 20, false)]

describe("payroll period summary", () => {
  test("counts drafts, confirmed and active employees without a statement", () => {
    const statements = [statement(1, 1, 9, "확정"), statement(2, 2, 9, "작성중"), statement(3, 1, 8, "확정")]
    expect(summarizePeriods(targets, statements, "2026-10")).toEqual([
      { period: "2026-10", drafts: 0, confirmed: 0, missing: 3 },
      { period: "2026-09", drafts: 1, confirmed: 1, missing: 1 },
      { period: "2026-08", drafts: 0, confirmed: 1, missing: 2 },
    ])
  })
  test("retired employees are never missing", () => {
    expect(missingEmployees(targets, [], "2026-10").map((employee) => employee.emp_no)).toEqual([1, 2, 3])
  })
})

describe("payroll helpers", () => {
  test("departments list unassigned employees last", () => {
    expect(departmentsOf(targets).map((department) => department.key)).toEqual(["10", "20", NO_DEPARTMENT])
    expect(employeesIn(targets, NO_DEPARTMENT).map((employee) => employee.emp_no)).toEqual([3])
    expect(employeesIn(targets, "").length).toBe(4)
  })
  test("blank amounts are not sent and periods are validated", () => {
    expect(itemsFromAmountValues({ BASE_PAY: "3000000", BONUS: " ", INCOME_TAX: "0" })).toEqual([
      { component_code: "BASE_PAY", amount: 3000000 },
      { component_code: "INCOME_TAX", amount: 0 },
    ])
    expect(isPeriod("2026-10")).toBe(true)
    expect(isPeriod("2026-13")).toBe(false)
    expect(isPeriod(null)).toBe(false)
  })
})

describe("previous month prefill", () => {
  test("finds the employee's statement for the month before, across years", () => {
    const statements = [statement(1, 1, 9, "확정"), statement(2, 2, 9, "확정")]
    expect(previousPeriod("2026-10")).toBe("2026-09")
    expect(previousPeriod("2026-01")).toBe("2025-12")
    expect(statementFor(statements, "1", previousPeriod("2026-10"))?.statement_id).toBe(1)
    expect(statementFor(statements, "1", previousPeriod("2026-09"))).toBeNull()
  })
})
