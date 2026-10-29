export type TenureStatus = "재직" | "휴직" | "퇴사"

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

// FN-HR-008 응답. 급여계좌 등 상세 개인정보는 포함하지 않는다.
export type RetiredEmployee = {
  emp_no: number
  person_id: number
  name: string
  dept_no: number | null
  dept_name: string | null
  position_code: string | null
  position_name: string | null
  email: string | null
  hire_date: string
  term_date: string
}

export type RoleSummary = {
  role_code: string
  role_name: string
}

export type EmployeeRoleAssignment = {
  employee_role_id: number
  emp_no: number
  role_code: string
  assigned_at: string
  revoked_at: string | null
}

// DRF DecimalField는 기본적으로 문자열로 직렬화한다.
export type Decimal = string

export type HistoryEntry = {
  history_id: number
  start_date: string
  end_date: string | null
  dept_no: number
  dept_name: string | null
  position_code: string
  position_name: string | null
  base_salary: Decimal
}

export type HistoryValues = {
  start_date: string
  end_date: string | null
  dept_no: number
  position_code: string
  base_salary: Decimal
}

export type HistoryChange = {
  history_id: number
  action: "발령" | "정정" | "취소" | string
  before: HistoryValues | null
  after: HistoryValues | null
  reason: string | null
  changed_by: number | null
  changed_at: string
  released_head_dept_nos: number[]
  restored_head_dept_nos: number[]
}

export type TransferResult = {
  history: HistoryEntry[]
  released_head_dept_nos: number[]
  restored_head_dept_nos: number[]
}

export type TransferPayload = {
  start_date: string
  dept_no: number
  position_code: string
  base_salary: string
  previous_base_salary?: string | null
  reason?: string | null
}

export type HistoryCorrectionPayload = {
  start_date: string
  dept_no: number
  position_code: string
  base_salary: string
  reason: string
}

// FN-HR-006 요청. 사번은 서버가 발급한다(HR-007).
export type NewHirePayload = {
  name: string
  birth_date: string
  gender: "M" | "F"
  email: string
  hire_date: string
  dept_no: number
  position_code: string
  phone: string | null
  extension_no: string | null
  address: string | null
  base_salary: string
  role_codes: string[]
  account: { password: string } | null
}

// FN-HR-009 요청. 인적사항은 보낼 때만 기존 Person을 갱신한다.
export type RehirePayload = Omit<NewHirePayload, "name" | "birth_date" | "gender">
  & Partial<Pick<NewHirePayload, "name" | "birth_date" | "gender">>

export type RegisteredEmployee = {
  emp_no: number
  person_id: number
  history_id: number
  name: string
  email: string
  dept_no: number
  position_code: string
  hire_date: string
  tenure_status: string
  account: { id: number; email: string } | null
  roles: { employee_role_id: number; role_code: string }[]
}

export type DepartmentPayload = {
  dept_no?: number
  dept_name: string
  parent_dept_no: number | null
  head_emp_no: number | null
}

export type EmployeeListFilters = {
  search?: string
  dept_no?: string
  tenure_status?: string
}

export type RetiredEmployeeFilters = {
  name?: string
  dept_no?: string
  emp_no?: string
  term_date_from?: string
  term_date_to?: string
}
