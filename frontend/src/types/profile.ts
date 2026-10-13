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
  can_process: boolean
}
