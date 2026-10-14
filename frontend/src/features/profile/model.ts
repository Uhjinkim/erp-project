import { routeHref } from "../../app/routing"
import type { ApprovalRequiredValues, ChangeRequestStatus } from "../../types/profile"

export type ChangeField = keyof ApprovalRequiredValues

export const CHANGE_FIELDS: { key: ChangeField; label: string }[] = [
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
  return date.toLocaleString("ko-KR", { dateStyle: "medium", timeStyle: "short" })
}

export type ContactForm = { phone: string; address: string }

// HR-002: 연락처·주소만 직접 수정한다. 빈 값은 미등록(null)으로 보낸다.
export function toContactPayload(form: ContactForm) {
  return { phone: form.phone.trim() || null, address: form.address.trim() || null }
}

export function contactChanged(form: ContactForm, current: { phone: string | null; address: string | null }) {
  const next = toContactPayload(form)
  return next.phone !== (current.phone ?? null) || next.address !== (current.address ?? null)
}

export type ChangeRequestForm = { email: string; bank_code: string; account_no: string }

// FN-HR-003 입력 안내. 현재 값과의 비교·이메일 중복·대기 요청 1건 제한은 서버가 최종 판단한다.
export function validateChangeRequest(form: ChangeRequestForm): Partial<Record<ChangeField | "form", string>> {
  const errors: Partial<Record<ChangeField | "form", string>> = {}
  const email = form.email.trim()
  const bank = form.bank_code.trim()
  const account = form.account_no.trim()
  if (!email && !bank && !account) errors.form = "변경할 사내 이메일 또는 급여계좌를 입력하세요."
  if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errors.email = "이메일 형식을 확인하세요."
  if (bank && !account) errors.account_no = "급여계좌는 은행 코드와 계좌번호를 함께 입력해야 합니다."
  if (account && !bank) errors.bank_code = "급여계좌는 은행 코드와 계좌번호를 함께 입력해야 합니다."
  return errors
}

// 입력하지 않은 항목은 보내지 않아 '변경하지 않음'으로 처리된다.
export function toChangeRequestPayload(form: ChangeRequestForm): Partial<ApprovalRequiredValues> {
  const payload: Partial<ApprovalRequiredValues> = {}
  if (form.email.trim()) payload.email = form.email.trim().toLowerCase()
  if (form.bank_code.trim()) payload.bank_code = form.bank_code.trim()
  if (form.account_no.trim()) payload.account_no = form.account_no.trim()
  return payload
}

export function firstFieldErrors(fieldErrors: Record<string, string[]>) {
  const result: Record<string, string> = {}
  for (const [key, messages] of Object.entries(fieldErrors)) {
    if (messages[0]) result[key] = messages[0]
  }
  return result
}
