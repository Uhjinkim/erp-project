import { requestJson } from "./client"
import type {
  DepartmentPayload,
  DepartmentSummary,
  EmployeeDetail,
  EmployeeListFilters,
  EmployeeRoleAssignment,
  EmployeeSummary,
  HistoryChange,
  HistoryCorrectionPayload,
  HistoryEntry,
  NewHirePayload,
  PositionSummary,
  RegisteredEmployee,
  RehirePayload,
  RetiredEmployee,
  RetiredEmployeeFilters,
  RoleSummary,
  TransferPayload,
  TransferResult,
} from "../types/workforce"

const jsonHeaders = { "Content-Type": "application/json" }
const base = "/api/workforce"

function post<T>(path: string, body: unknown, method = "POST") {
  return requestJson<T>(path, { method, headers: jsonHeaders, body: JSON.stringify(body) })
}

function query(values: Record<string, string | undefined>) {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(values)) {
    if (value?.trim()) params.set(key, value.trim())
  }
  const text = params.toString()
  return text ? `?${text}` : ""
}

// HR-001: 사원 목록은 인사관리자만 조회할 수 있다. 다른 모듈의 대상 조회로 사용하지 않는다(INT-01).
export function listEmployees(filters: EmployeeListFilters = {}) {
  return requestJson<EmployeeSummary[]>(`${base}/employees/${query(filters)}`)
}

export function getEmployeeDetail(empNo: number) {
  return requestJson<EmployeeDetail>(`${base}/employees/${empNo}/`)
}

// FN-HR-008: 퇴사자 조회(HR-005, 인사관리자 전용).
export function listRetiredEmployees(filters: RetiredEmployeeFilters = {}) {
  return requestJson<RetiredEmployee[]>(`${base}/employees/terminated/${query(filters)}`)
}

// FN-HR-006: 사원·최초 인사이력·역할·계정을 서버가 한 번에 등록한다.
export function registerNewHire(payload: NewHirePayload) {
  return post<RegisteredEmployee>(`${base}/new-hires/`, payload)
}

// FN-HR-009: 기존 Person에 새 사번의 고용을 추가한다(HR-006).
export function rehirePerson(personId: number, payload: RehirePayload) {
  return post<RegisteredEmployee>(`${base}/persons/${personId}/rehire/`, payload)
}

// FN-HR-007: 상태·퇴사일만 바꾸고 다른 기록은 보존한다(HR-005, HR-009).
export function terminateEmployee(empNo: number, termDate: string) {
  return post<EmployeeDetail>(`${base}/employees/${empNo}/terminate/`, { term_date: termDate })
}

// FN-HR-010 인사이력·발령.
export function getEmploymentHistory(empNo: number) {
  return requestJson<HistoryEntry[]>(`${base}/employees/${empNo}/history/`)
}

export function getHistoryChanges(empNo: number) {
  return requestJson<HistoryChange[]>(`${base}/employees/${empNo}/history/changes/`)
}

export function transferEmployee(empNo: number, payload: TransferPayload) {
  return post<TransferResult>(`${base}/employees/${empNo}/history/`, payload)
}

export function correctHistory(empNo: number, historyId: number, payload: HistoryCorrectionPayload) {
  return post<TransferResult>(`${base}/employees/${empNo}/history/${historyId}/correct/`, payload)
}

export function cancelHistory(empNo: number, historyId: number, reason: string) {
  return post<TransferResult>(`${base}/employees/${empNo}/history/${historyId}/cancel/`, { reason })
}

// 역할 부여·회수. 계정 CRUD는 system 모듈 범위다.
export function listRoles() {
  return requestJson<RoleSummary[]>(`${base}/roles/`)
}

export function listEmployeeRoles(empNo: number) {
  return requestJson<EmployeeRoleAssignment[]>(`${base}/employees/${empNo}/roles/`)
}

export function assignEmployeeRole(empNo: number, roleCode: string) {
  return post<EmployeeRoleAssignment>(`${base}/employees/${empNo}/roles/`, { role_code: roleCode })
}

export function revokeEmployeeRole(empNo: number, assignmentId: number) {
  return post<EmployeeRoleAssignment>(`${base}/employees/${empNo}/roles/${assignmentId}/revoke/`, {})
}

// 부서·직급 조회는 인증 사용자 모두, 변경은 인사관리자만 가능하다.
export function listDepartments() {
  return requestJson<DepartmentSummary[]>(`${base}/departments/`)
}

export function listPositions() {
  return requestJson<PositionSummary[]>(`${base}/positions/`)
}

export function createDepartment(payload: DepartmentPayload) {
  return post<DepartmentSummary>(`${base}/departments/`, payload)
}

export function updateDepartment(deptNo: number, payload: Omit<DepartmentPayload, "dept_no">) {
  return post<DepartmentSummary>(`${base}/departments/${deptNo}/`, payload, "PATCH")
}

export function createPosition(payload: PositionSummary) {
  return post<PositionSummary>(`${base}/positions/`, payload)
}

export function updatePosition(code: string, payload: Omit<PositionSummary, "position_code">) {
  return post<PositionSummary>(`${base}/positions/${encodeURIComponent(code)}/`, payload, "PATCH")
}
