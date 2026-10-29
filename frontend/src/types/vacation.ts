export type VacationStatus = "대기" | "승인" | "반려" | "취소" | "회수"
export type VacationDecimal = string | number
export type VacationType = {
  balance_type_id?: string
  remaining_days?: string | null
  type_id: string
  type_name: string
  is_paid: boolean
  deduct_days: VacationDecimal
}
export type VacationRequest = {
  request_id: number
  employee_no: number
  type_id: string
  start_datetime: string
  end_datetime: string
  use_days: VacationDecimal
  status: VacationStatus
  approver_no: number
  approved_at: string | null
  reject_reason: string | null
  request_reason: string | null
}

export type VacationInput = {
  type_id: string
  start_datetime: string
  end_datetime: string
  use_days: string
  reason: string
}

export type VacationAction = "cancel" | "approve" | "reject" | "recall"

export type VacationSnapshot = {
  type_id: string
  start_datetime: string
  end_datetime: string
  use_days: VacationDecimal
  approver_no: number
  request_reason: string | null
  approved_at: string | null
  reject_reason: string | null
  balance_deducted?: boolean
}

export type VacationHistory = {
  history_id: number
  request_id: number
  from_status: VacationStatus | null
  to_status: VacationStatus
  actor_employee_no: number
  reason: string | null
  changed_at: string
  before_values?: VacationSnapshot | null
  after_values?: VacationSnapshot | null
}
