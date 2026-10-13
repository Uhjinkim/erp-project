import type { VacationAction, VacationHistory, VacationInput, VacationRequest, VacationSnapshot, VacationType } from "../../types/vacation"

export const statuses = ["대기", "승인", "반려", "취소", "회수"] as const

export function requestIdFromSearch(search = "") {
  const value = new URLSearchParams(search).get("requestId")
  if (!value || !/^[1-9]\d*$/.test(value)) return null
  const id = Number(value)
  return Number.isSafeInteger(id) ? id : null
}

export function localDateTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ""
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 19)
}

export function displayDateTime(value: string | null) {
  if (!value) return "—"
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? "확인 필요" : date.toLocaleString("ko-KR")
}

export function formFromRequest(item?: VacationRequest): VacationInput {
  return {
    type_id: item?.type_id ?? "",
    start_datetime: item ? localDateTime(item.start_datetime) : "",
    end_datetime: item ? localDateTime(item.end_datetime) : "",
    use_days: item ? String(item.use_days) : "1.00",
    reason: item?.request_reason ?? "",
  }
}

export function validateInput(input: VacationInput) {
  const errors: Record<string, string> = {}
  if (!input.type_id) errors.type_id = "휴가 유형을 선택하세요."
  const start = new Date(input.start_datetime).getTime()
  const end = new Date(input.end_datetime).getTime()
  if (!Number.isFinite(start)) errors.start_datetime = "시작 일시를 입력하세요."
  if (!Number.isFinite(end)) errors.end_datetime = "종료 일시를 입력하세요."
  if (Number.isFinite(start) && Number.isFinite(end) && end < start) errors.end_datetime = "종료 일시는 시작보다 빠를 수 없습니다."
  if (!/^\d(\.\d{1,2})?$/.test(input.use_days) || Number(input.use_days) < 0.01) errors.use_days = "0.01~9.99일을 소수 둘째 자리까지 입력하세요."
  if (input.reason.length > 255) errors.reason = "사유는 255자까지 입력할 수 있습니다."
  return errors
}

export function transportInput(input: VacationInput): VacationInput {
  return { ...input, start_datetime: new Date(input.start_datetime).toISOString(), end_datetime: new Date(input.end_datetime).toISOString() }
}

// UI guidance for LV-005~007; the server remains responsible for authorization.
export function availableActions(item: VacationRequest, employeeNo: number): VacationAction[] {
  const actions: VacationAction[] = []
  if (item.status === "대기" && item.employee_no === employeeNo) actions.push("cancel")
  if (item.status === "대기" && item.approver_no === employeeNo) actions.push("approve", "reject")
  if (item.status === "승인" && item.approver_no === employeeNo) actions.push("recall")
  return actions
}

export function canResubmit(item: VacationRequest, employeeNo: number) {
  return item.status === "회수" && item.employee_no === employeeNo
}

export function filterRequests(items: VacationRequest[], search: string) {
  const params = new URLSearchParams(search)
  const status = params.get("status") ?? ""
  const type = params.get("type") ?? ""
  const query = (params.get("q") ?? "").trim()
  const from = params.get("from") ?? ""
  const to = params.get("to") ?? ""
  return items.filter((item) => {
    const date = localDateTime(item.start_datetime).slice(0, 10)
    return (!status || item.status === status) && (!type || item.type_id === type)
      && (!query || String(item.request_id).includes(query) || String(item.employee_no).includes(query))
      && (!from || date >= from) && (!to || date <= to)
  }).sort((a, b) => params.get("order") === "asc" ? a.request_id - b.request_id : b.request_id - a.request_id)
}

export function typeName(id: string, types: VacationType[]) {
  return types.find((type) => type.type_id === id)?.type_name ?? id
}

const snapshotLabels: Record<keyof VacationSnapshot, string> = {
  type_id: "휴가 유형", start_datetime: "시작 일시", end_datetime: "종료 일시", use_days: "사용 일수",
  approver_no: "승인자 사번", request_reason: "신청 사유", approved_at: "승인 일시",
  reject_reason: "반려 사유", balance_deducted: "잔여 차감 반영",
}

export function snapshotChanges(entry: VacationHistory, types: VacationType[]) {
  if (!entry.before_values || !entry.after_values) return null
  const before = entry.before_values
  const after = entry.after_values
  const display = (key: keyof VacationSnapshot, value: VacationSnapshot[typeof key]) => {
    if (value == null) return "—"
    if (key === "type_id") return typeName(String(value), types)
    if (key === "start_datetime" || key === "end_datetime" || key === "approved_at") return displayDateTime(String(value))
    if (typeof value === "boolean") return value ? "반영" : "미반영"
    return String(value)
  }
  return (Object.keys(snapshotLabels) as (keyof VacationSnapshot)[])
    .filter((key) => key === "use_days" ? Number(before[key]) !== Number(after[key]) : String(before[key] ?? "") !== String(after[key] ?? ""))
    .map((key) => ({ key, label: snapshotLabels[key], before: display(key, before[key]), after: display(key, after[key]) }))
}
