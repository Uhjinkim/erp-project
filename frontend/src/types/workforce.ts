export type EmployeeSummary = {
  emp_no: number
  person_id: number
  name: string
  dept_no: number | null
  position_code: string | null
  tenure_status: string
  email: string | null
  phone: string | null
  extension_no: string | null
  hire_date: string
  term_date: string | null
}

export type DepartmentSummary = {
  dept_no: number
  dept_name: string
  parent_dept_no: number | null
  head_emp_no: number | null
}

export type PositionSummary = {
  position_code: string
  position_name: string
  sort_order: number
}
