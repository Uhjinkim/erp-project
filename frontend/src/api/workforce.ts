import { requestJson } from "./client"
import type {
  DepartmentSummary,
  EmployeeDetail,
  EmployeeSummary,
  PositionSummary,
} from "../types/workforce"

// 사원 목록은 HR-001에 따라 인사관리자만 조회할 수 있다. 다른 모듈의 호출 방식은 결정 대기 중.
export async function loadWorkforce(includeEmployees = true) {
  const [employees, departments, positions] = await Promise.all([
    includeEmployees
      ? requestJson<EmployeeSummary[]>("/api/workforce/employees/")
      : Promise.resolve<EmployeeSummary[]>([]),
    requestJson<DepartmentSummary[]>("/api/workforce/departments/"),
    requestJson<PositionSummary[]>("/api/workforce/positions/"),
  ])
  return { employees, departments, positions }
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
