import { afterAll, beforeEach, describe, expect, mock, test } from "bun:test"

mock.module("../src/config/environment", () => ({ environment: { apiBaseUrl: "", apiTimeoutMs: 1000 } }))
const model = await import("../src/features/workforce/model")
const api = await import("../src/api/workforce")
import type { EmployeeRoleAssignment, HistoryEntry } from "../src/types/workforce"

const previousFetch = globalThis.fetch
const previousWindow = Object.getOwnPropertyDescriptor(globalThis, "window")
const previousDocument = Object.getOwnPropertyDescriptor(globalThis, "document")
Object.defineProperty(globalThis, "window", { configurable: true, value: { setTimeout, clearTimeout } })
Object.defineProperty(globalThis, "document", { configurable: true, value: { cookie: "csrftoken=synthetic" } })
afterAll(() => {
  globalThis.fetch = previousFetch
  if (previousWindow) Object.defineProperty(globalThis, "window", previousWindow)
  else Reflect.deleteProperty(globalThis, "window")
  if (previousDocument) Object.defineProperty(globalThis, "document", previousDocument)
  else Reflect.deleteProperty(globalThis, "document")
})

let calls: { path: string; method: string; body: unknown }[] = []
beforeEach(() => {
  calls = []
  globalThis.fetch = mock(async (input: RequestInfo | URL, options?: RequestInit) => {
    calls.push({ path: String(input), method: options?.method ?? "GET", body: options?.body ? JSON.parse(String(options.body)) : undefined })
    return new Response("[]", { status: 200 })
  }) as unknown as typeof fetch
})

const user = (roles: string[], is_superuser = false) => ({ id: 1, email: "synthetic@example.test", is_staff: false, is_superuser, employee: null, roles })
const entry = (history_id: number, start_date: string, end_date: string | null = null): HistoryEntry => ({
  history_id, start_date, end_date, dept_no: 1, dept_name: null, position_code: "P1", position_name: null, base_salary: "1000.00",
})

describe("workforce display rules", () => {
  test("HR screen gate allows HR_MANAGER and superuser like the server", () => {
    expect(model.isHRManager(user(["HR_MANAGER"]))).toBe(true)
    expect(model.isHRManager(user(["PAYROLL_MANAGER", "HR_MANAGER"]))).toBe(true)
    expect(model.isHRManager(user([], true))).toBe(true)
    expect(model.isHRManager(user(["PAYROLL_MANAGER", "HR_LEAVE_APPROVER"]))).toBe(false)
  })

  test("route ids accept positive integers only", () => {
    expect(model.parseId("12")).toBe(12)
    for (const value of [null, "", "0", "-1", "1.5", "12abc", "99999999999999999999"]) expect(model.parseId(value)).toBeNull()
  })

  test("module links keep query keys and drop empty ones", () => {
    expect(model.workforceHref("employee-detail", { empNo: 7, tab: undefined })).toBe("#/workforce/employee-detail?empNo=7")
    expect(model.workforceHref("employee-list", { q: "", status: "재직" })).toBe(`#/workforce/employee-list?status=${encodeURIComponent("재직")}`)
    expect(model.workforceHref("org")).toBe("#/workforce/org")
  })

  test("account numbers are masked by default", () => {
    expect(model.maskAccount("1234567890")).toBe("******7890")
    expect(model.maskAccount("123")).toBe("****123")
    expect(model.maskAccount(null)).toBe("미등록")
  })

  test("only the latest open history entry is offered for correction or cancellation", () => {
    const history = [entry(1, "2024-01-01", "2024-12-31"), entry(3, "2025-01-01"), entry(2, "2025-01-01", "2024-12-31")]
    expect(model.latestHistory(history)?.history_id).toBe(3)
    expect(model.sortHistoryDesc(history).map((item) => item.history_id)).toEqual([3, 2, 1])
    expect(model.latestHistory([])).toBeNull()
  })

  test("roles with an active assignment are not offered again", () => {
    const roles = [{ role_code: "HR_MANAGER", role_name: "인사 관리자" }, { role_code: "PAYROLL_MANAGER", role_name: "급여담당자" }]
    const assignments: EmployeeRoleAssignment[] = [
      { employee_role_id: 1, emp_no: 5, role_code: "HR_MANAGER", assigned_at: "2025-01-01T00:00:00Z", revoked_at: null },
      { employee_role_id: 2, emp_no: 5, role_code: "PAYROLL_MANAGER", assigned_at: "2025-01-01T00:00:00Z", revoked_at: "2025-02-01T00:00:00Z" },
    ]
    expect(model.assignableRoles(roles, assignments).map((role) => role.role_code)).toEqual(["PAYROLL_MANAGER"])
    expect(model.activeAssignments(assignments)).toHaveLength(1)
  })

  test("client pages clamp to the available range", () => {
    const items = Array.from({ length: 45 }, (_, index) => index)
    expect(model.pageOf(items, 3)).toEqual({ items: [40, 41, 42, 43, 44], page: 3, pages: 3 })
    expect(model.pageOf(items, 9).page).toBe(3)
    expect(model.pageOf([], 1)).toEqual({ items: [], page: 1, pages: 1 })
  })
})

describe("employment form", () => {
  const filled = { ...model.emptyEmploymentForm("2026-10-01"), name: " 합성 사원 ", birth_date: "1990-01-01", gender: "F" as const, email: " new@example.test ", dept_no: "10", position_code: "P1", base_salary: "3000000", phone: " ", role_codes: ["HR_MANAGER"] }

  test("new hire requires person, employment, and salary fields", () => {
    const errors = model.validateEmploymentForm(model.emptyEmploymentForm(), "create")
    expect(Object.keys(errors).sort()).toEqual(["base_salary", "birth_date", "dept_no", "email", "gender", "hire_date", "name", "position_code"].sort())
    expect(model.validateEmploymentForm(filled, "create")).toEqual({})
    expect(model.validateEmploymentForm({ ...filled, base_salary: "-1" }, "create").base_salary).toBeDefined()
    expect(model.validateEmploymentForm({ ...filled, base_salary: "1.234" }, "create").base_salary).toBeDefined()
    expect(model.validateEmploymentForm({ ...filled, create_account: true, password: "short" }, "create").password).toBeDefined()
  })

  test("new hire payload trims values, sends nulls for blanks, and never sends emp_no", () => {
    const payload = model.toNewHirePayload({ ...filled, create_account: true, password: "synthetic-pass" })
    expect(payload).toMatchObject({ name: "합성 사원", email: "new@example.test", dept_no: 10, phone: null, base_salary: "3000000", role_codes: ["HR_MANAGER"], account: { password: "synthetic-pass" } })
    expect("emp_no" in payload).toBe(false)
  })

  test("rehire keeps existing person values unless the HR manager enters them", () => {
    const rehire = { ...filled, name: "", birth_date: "", gender: "" as const }
    expect(model.validateEmploymentForm(rehire, "rehire")).toEqual({})
    const payload = model.toRehirePayload(rehire)
    expect("name" in payload || "birth_date" in payload || "gender" in payload).toBe(false)
    expect(model.toRehirePayload({ ...rehire, name: "새 이름" }).name).toBe("새 이름")
  })

  test("server field errors map to form fields, nested account errors to the password", () => {
    expect(model.firstFieldErrors({ email: ["중복", "기타"], account: ["짧음"], empty: [] })).toEqual({ email: "중복", password: "짧음" })
  })
})

describe("workforce API contract", () => {
  test("list filters go to the server query and blank values are omitted", async () => {
    await api.listEmployees({ search: " kim ", dept_no: "", tenure_status: "재직" })
    expect(calls[0].path).toBe(`/api/workforce/employees/?search=kim&tenure_status=${encodeURIComponent("재직")}`)
    await api.listRetiredEmployees({ term_date_from: "2025-01-01", name: "" })
    expect(calls[1].path).toBe("/api/workforce/employees/terminated/?term_date_from=2025-01-01")
  })

  test("lifecycle commands use the dedicated server endpoints instead of multiple PATCH calls", async () => {
    await api.terminateEmployee(5, "2026-10-01")
    await api.rehirePerson(9, { ...model.toRehirePayload({ ...model.emptyEmploymentForm("2026-10-01"), email: "a@example.test", dept_no: "1", position_code: "P1", base_salary: "0" }) })
    await api.cancelHistory(5, 33, "사유")
    await api.revokeEmployeeRole(5, 2)
    expect(calls.map((call) => `${call.method} ${call.path}`)).toEqual([
      "POST /api/workforce/employees/5/terminate/",
      "POST /api/workforce/persons/9/rehire/",
      "POST /api/workforce/employees/5/history/33/cancel/",
      "POST /api/workforce/employees/5/roles/2/revoke/",
    ])
    expect(calls[0].body).toEqual({ term_date: "2026-10-01" })
    expect(calls[2].body).toEqual({ reason: "사유" })
  })

  test("organization edits patch only editable fields", async () => {
    await api.updateDepartment(10, { dept_name: "인사팀", parent_dept_no: null, head_emp_no: 3 })
    await api.updatePosition("P 1", { position_name: "사원", sort_order: 1 })
    expect(calls[0]).toEqual({ path: "/api/workforce/departments/10/", method: "PATCH", body: { dept_name: "인사팀", parent_dept_no: null, head_emp_no: 3 } })
    expect(calls[1].path).toBe("/api/workforce/positions/P%201/")
  })
})
