import { requestJson } from "./client"
import type {
  ApprovalRequiredValues,
  ChangeRequestStatus,
  DepartmentSummary,
  EmployeeDetail,
  EmployeeSummary,
  PersonalInfoChangeRequest,
  PositionSummary,
} from "../types/workforce"

export async function loadWorkforce(includeEmployees: boolean) {
  const [employees, departments, positions] = await Promise.all([
    includeEmployees
      ? requestJson<EmployeeSummary[]>("/api/workforce/employees/")
      : Promise.resolve<EmployeeSummary[]>([]),
    requestJson<DepartmentSummary[]>("/api/workforce/departments/"),
    requestJson<PositionSummary[]>("/api/workforce/positions/"),
  ])
  return { employees, departments, positions }
}

export async function getMyEmployeeInfo() {
  return requestJson<EmployeeDetail>("/api/workforce/employees/me/")
}

export async function getEmployeeDetail(empNo: number) {
  return requestJson<EmployeeDetail>(`/api/workforce/employees/${empNo}/`)
}

export async function createDepartment(deptNo: number, deptName: string) {
  return requestJson<DepartmentSummary>("/api/workforce/departments/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      dept_no: deptNo,
      dept_name: deptName,
      parent_dept_no: null,
      head_emp_no: null,
    }),
  })
}

const jsonHeaders = { "Content-Type": "application/json" }
const changeRequestsPath = "/api/workforce/personal-info-requests/"

export async function updateMyContact(values: { phone: string | null, address: string | null }) {
  return requestJson<EmployeeDetail>("/api/workforce/employees/me/", {
    method: "PATCH",
    headers: jsonHeaders,
    body: JSON.stringify(values),
  })
}

export async function listChangeRequests(
  options: { status?: ChangeRequestStatus, processable?: boolean, mine?: boolean } = {},
) {
  const params = new URLSearchParams()
  if (options.status) params.set("status", options.status)
  if (options.processable) params.set("processable", "true")
  if (options.mine) params.set("mine", "true")
  const query = params.toString() ? `?${params}` : ""
  return requestJson<PersonalInfoChangeRequest[]>(`${changeRequestsPath}${query}`)
}

export async function createChangeRequest(values: Partial<ApprovalRequiredValues>) {
  return requestJson<PersonalInfoChangeRequest>(changeRequestsPath, {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify(values),
  })
}

export async function processChangeRequest(
  requestId: number,
  action: "approve" | "reject" | "cancel",
  reason?: string,
) {
  return requestJson<PersonalInfoChangeRequest>(`${changeRequestsPath}${requestId}/${action}/`, {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify(reason ? { reason } : {}),
  })
}
