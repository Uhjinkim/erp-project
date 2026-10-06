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

export type EmployeeDetail = {
  emp_no: number
  person_id: number
  name: string
  birth_date: string | null
  gender: string | null
  dept_no: number | null
  dept_name: string | null
  position_code: string | null
  position_name: string | null
  tenure_status: string
  email: string | null
  phone: string | null
  extension_no: string | null
  address: string | null
  bank_code: string | null
  account_no: string | null
  hire_date: string
  term_date: string | null
}

export type ChangeRequestStatus = "대기" | "승인" | "반려" | "취소"

export type ApprovalRequiredValues = {
  email: string | null
  bank_code: string | null
  account_no: string | null
}

export type PersonalInfoChangeRequest = {
  request_id: number
  emp_no: number
  status: ChangeRequestStatus
  previous: ApprovalRequiredValues
  requested: ApprovalRequiredValues
  changed_fields: (keyof ApprovalRequiredValues)[]
  requested_at: string
  processed_by: number | null
  processed_at: string | null
  reject_reason: string | null
}
