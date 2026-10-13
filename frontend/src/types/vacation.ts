export type VacationStatus = "대기" | "승인" | "반려" | "취소" | "회수"
export type VacationType = { type_id: string; type_name: string; is_paid: boolean; deduct_days: string }
export type VacationRequest = {
  request_id: number
  employee_no: number
  type_id: string
  start_datetime: string
  end_datetime: string
  use_days: string
  status: VacationStatus
  approver_no: number
  approved_at: string | null
  reject_reason: string | null
  request_reason: string | null
}
