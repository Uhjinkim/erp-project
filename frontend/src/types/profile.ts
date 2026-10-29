export type ChangeRequestStatus = "대기" | "승인" | "반려" | "취소"

// HR-002: 수정 요청과 인사관리자 승인을 거쳐 반영되는 항목. 연락처·주소의 빈 문자열은 미등록으로 지우는 요청이다.
export type ApprovalRequiredValues = {
  phone: string | null
  address: string | null
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
