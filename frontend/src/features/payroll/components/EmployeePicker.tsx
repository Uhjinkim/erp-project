import { Select } from "../../../components/ui"
import type { PayrollTargetEmployee } from "../../../types/payroll"
import { departmentsOf, employeesIn } from "../model"

type EmployeePickerProps = {
  targets: PayrollTargetEmployee[]
  deptKey: string
  empNo: string
  onChange: (deptKey: string, empNo: string) => void
  // Filter mode offers "전체"; create mode requires a department before a person.
  mode: "filter" | "create"
  disabled?: boolean
  ownEmployeeNo?: number | null
}

export function EmployeePicker({ targets, deptKey, empNo, onChange, mode, disabled = false, ownEmployeeNo }: EmployeePickerProps) {
  const departments = departmentsOf(targets)
  const candidates = mode === "create" && !deptKey ? [] : employeesIn(targets, deptKey)
  const personPlaceholder = mode === "filter" ? "전체 사람" : deptKey ? "사람 선택" : "부서를 먼저 선택하세요"
  return (
    <>
      <Select label="부서" value={deptKey} disabled={disabled} onChange={(event) => onChange(event.target.value, "")}>
        <option value="">{mode === "filter" ? "전체 부서" : "부서 선택"}</option>
        {departments.map((department) => (
          <option key={department.key} value={department.key}>
            {department.name}
          </option>
        ))}
      </Select>
      <Select
        label="사람"
        value={empNo}
        required={mode === "create"}
        disabled={disabled || (mode === "create" && !deptKey)}
        onChange={(event) => onChange(deptKey, event.target.value)}
      >
        <option value="">{personPlaceholder}</option>
        {candidates.map((employee) => (
          <option key={employee.emp_no} value={employee.emp_no} disabled={mode === "create" && employee.emp_no === ownEmployeeNo}>
            {employee.name} ({employee.emp_no}){employee.is_active ? "" : " · 퇴사"}{mode === "create" && employee.emp_no === ownEmployeeNo ? " · 본인(생성 불가)" : ""}
          </option>
        ))}
      </Select>
    </>
  )
}
