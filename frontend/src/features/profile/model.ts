import { BUSINESS_TIME_ZONE } from "../../utils/dateTime"
import { routeHref } from "../../app/routing"
import type { ApprovalRequiredValues, ChangeRequestStatus } from "../../types/profile"

export type ChangeField = keyof ApprovalRequiredValues

export const CHANGE_FIELDS: { key: ChangeField; label: string }[] = [
  { key: "phone", label: "연락처" },
  { key: "address", label: "주소" },
  { key: "email", label: "사내 이메일" },
  { key: "bank_code", label: "은행 코드" },
  { key: "account_no", label: "급여계좌" },
]
export const CHANGE_STATUSES: ChangeRequestStatus[] = ["대기", "승인", "반려", "취소"]

export function fieldLabel(field: ChangeField) {
  return CHANGE_FIELDS.find((item) => item.key === field)?.label ?? field
}

export function profileHref(screenId: string, params: Record<string, string | number | undefined> = {}) {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") search.set(key, String(value))
  }
  return routeHref({ moduleId: "profile", screenId, search: search.toString() })
}

export function navigate(href: string) {
  window.location.hash = href
}

export function parseId(value: string | null): number | null {
  if (!value || !/^\d+$/.test(value)) return null
  const id = Number(value)
  return Number.isSafeInteger(id) && id > 0 ? id : null
}

export function statusTone(status: string): "info" | "success" | "error" | "neutral" {
  if (status === "대기") return "info"
  if (status === "승인") return "success"
  if (status === "반려") return "error"
  return "neutral"
}

export function parseStatus(value: string | null): ChangeRequestStatus | undefined {
  return CHANGE_STATUSES.find((status) => status === value)
}

// 기본 표시는 마지막 4자리만 남긴다. 서버가 이미 가린 값은 그대로 둔다.
export function maskAccount(account: string | null) {
  if (!account) return "미등록"
  if (account.includes("*")) return account
  const characters = [...account].filter((character) => /[\p{L}\p{N}]/u.test(character))
  if (characters.length <= 4) return "*".repeat(characters.length)
  return `${"*".repeat(characters.length - 4)}${characters.slice(-4).join("")}`
}

export function displayValue(field: ChangeField, value: string | null) {
  if (value === null || value === "") return "미등록"
  return field === "account_no" ? maskAccount(value) : value
}

export function formatDateTime(value: string | null) {
  if (!value) return "-"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString("ko-KR", { timeZone: BUSINESS_TIME_ZONE, dateStyle: "medium", timeStyle: "short" })
}

export type ProfileEditForm = { phone: string; address: string; email: string; bank_code: string; account_no: string }

// 수정 모드 시작 값. 계좌번호는 원문을 입력칸에 띄우지 않고, 바꿀 때만 새로 입력받는다.
export function toEditForm(current: ApprovalRequiredValues): ProfileEditForm {
  return { phone: current.phone ?? "", address: current.address ?? "", email: current.email ?? "", bank_code: current.bank_code ?? "", account_no: "" }
}

// HR-002: 바뀐 항목만 수정 요청으로 보낸다. 연락처·주소를 비우면 미등록으로 지우는 요청("")이 된다.
export function toEditPayload(form: ProfileEditForm, current: ApprovalRequiredValues): Partial<ApprovalRequiredValues> {
  const payload: Partial<ApprovalRequiredValues> = {}
  const phone = form.phone.trim()
  const address = form.address.trim()
  const email = form.email.trim().toLowerCase()
  const bank = form.bank_code.trim()
  const account = form.account_no.trim()
  if (phone !== (current.phone ?? "")) payload.phone = phone
  if (address !== (current.address ?? "")) payload.address = address
  if (email !== (current.email ?? "").toLowerCase()) payload.email = email
  // 계좌는 은행 코드와 계좌번호를 함께 바꾼다.
  if (account || bank !== (current.bank_code ?? "")) {
    payload.bank_code = bank
    payload.account_no = account
  }
  return payload
}

// FN-HR-002 입력 안내. 현재 값과의 비교·이메일 중복·대기 요청 1건 제한은 서버가 최종 판단한다.
export function validateEdit(form: ProfileEditForm, current: ApprovalRequiredValues): Partial<Record<ChangeField | "form", string>> {
  const errors: Partial<Record<ChangeField | "form", string>> = {}
  const payload = toEditPayload(form, current)
  if (Object.keys(payload).length === 0) errors.form = "수정된 내용이 없습니다."
  if (payload.email === "") errors.email = "사내 이메일은 비워 둘 수 없습니다."
  else if (payload.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(payload.email)) errors.email = "이메일 형식을 확인하세요."
  if ("account_no" in payload) {
    if (!payload.bank_code) errors.bank_code = "급여계좌는 은행 코드와 계좌번호를 함께 입력해야 합니다."
    if (!payload.account_no) errors.account_no = "계좌를 바꾸려면 새 계좌번호를 입력하세요."
  }
  return errors
}

export function firstFieldErrors(fieldErrors: Record<string, string[]>) {
  const result: Record<string, string> = {}
  for (const [key, messages] of Object.entries(fieldErrors)) {
    if (messages[0]) result[key] = messages[0]
  }
  return result
}
