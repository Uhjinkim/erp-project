import { requestJson } from "./client"
import type { DepartmentSummary, EmployeeSummary, PositionSummary } from "../types/workforce"

export async function loadWorkforce() {
  const [employees, departments, positions] = await Promise.all([
    requestJson<EmployeeSummary[]>("/api/workforce/employees/"),
    requestJson<DepartmentSummary[]>("/api/workforce/departments/"),
    requestJson<PositionSummary[]>("/api/workforce/positions/"),
  ])
  return { employees, departments, positions }
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
