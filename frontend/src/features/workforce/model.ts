import { routeHref } from "../../app/routing"
import type { CurrentUser } from "../../types/auth"
import type {
  DepartmentSummary,
  EmployeeRoleAssignment,
  HistoryEntry,
  NewHirePayload,
  PositionSummary,
  RehirePayload,
  RoleSummary,
} from "../../types/workforce"

export const HR_MANAGER_ROLE = "HR_MANAGER"
export const TENURE_STATUSES = ["재직", "휴직", "퇴사"] as const
export const PAGE_SIZE = 20

// 사원·조직 메뉴는 HR_MANAGER 역할 계정에게만 보인다(2026-10-27 결정, superuser도 역할이 있어야 함).
// 화면 안내용 판정이며 실제 권한은 workforce API가 HR-001·HR-005에 따라 검사한다.
export function isHRManager(user: CurrentUser) {
  return user.roles.includes(HR_MANAGER_ROLE)
}

export function workforceHref(screenId: string, params: Record<string, string | number | undefined> = {}) {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") search.set(key, String(value))
  }
  return routeHref({ moduleId: "workforce", screenId, search: search.toString() })
}

// 사번은 양의 정수만 허용한다. 잘못된 값은 "선택 안 됨"으로 본다.
export function parseId(value: string | null): number | null {
  if (!value || !/^\d+$/.test(value)) return null
  const id = Number(value)
  return Number.isSafeInteger(id) && id > 0 ? id : null
}

export function tenureTone(status: string): "success" | "warning" | "neutral" {
  if (status === "재직") return "success"
  if (status === "휴직") return "warning"
  return "neutral"
}

export function genderLabel(gender: string | null) {
  if (gender === "M") return "남성"
  if (gender === "F") return "여성"
  return gender ?? "미등록"
}

// 상세 화면의 기본 표시는 마지막 4자리만 남긴다(HR-02 원문 노출 최소화).
export function maskAccount(account: string | null) {
  if (!account) return "미등록"
  const visible = account.slice(-4)
  return `${"*".repeat(Math.max(account.length - 4, 4))}${visible}`
}

export function formatAmount(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") return "-"
  const amount = Number(value)
  if (!Number.isFinite(amount)) return String(value)
  return `${amount.toLocaleString("ko-KR", { maximumFractionDigits: 2 })}원`
}

export function formatDateTime(value: string | null) {
  if (!value) return "-"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString("ko-KR", { dateStyle: "medium", timeStyle: "short" })
}

// 날짜 입력의 기본값과 max에 사용하는 로컬 기준 오늘(YYYY-MM-DD).
export function localToday(now = new Date()) {
  const offset = now.getTimezoneOffset() * 60_000
  return new Date(now.getTime() - offset).toISOString().slice(0, 10)
}

export function departmentLabel(departments: DepartmentSummary[], deptNo: number | null) {
  if (deptNo === null) return "미배정"
  return departments.find((item) => item.dept_no === deptNo)?.dept_name ?? `부서 #${deptNo}`
}

export function positionLabel(positions: PositionSummary[], code: string | null) {
  if (!code) return "미배정"
  return positions.find((item) => item.position_code === code)?.position_name ?? code
}

export function roleLabel(roles: RoleSummary[], code: string) {
  return roles.find((item) => item.role_code === code)?.role_name ?? code
}

export function sortPositions(positions: PositionSummary[]) {
  return [...positions].sort((a, b) => a.sort_order - b.sort_order || a.position_code.localeCompare(b.position_code))
}

export function activeAssignments(assignments: EmployeeRoleAssignment[]) {
  return assignments.filter((item) => item.revoked_at === null)
}

// 이미 활성 상태인 역할은 부여 선택지에서 뺀다. 중복 부여 거절은 서버가 최종 판단한다.
export function assignableRoles(roles: RoleSummary[], assignments: EmployeeRoleAssignment[]) {
  const active = new Set(activeAssignments(assignments).map((item) => item.role_code))
  return roles.filter((role) => !active.has(role.role_code))
}

// 정정·취소는 최근 이력에만 안내한다. 대상 허용 여부는 서버가 FN-HR-010 규칙으로 판정한다.
export function latestHistory(history: HistoryEntry[]) {
  return history.reduce<HistoryEntry | null>((latest, item) => {
    if (!latest) return item
    if (item.start_date > latest.start_date) return item
    if (item.start_date === latest.start_date && item.history_id > latest.history_id) return item
    return latest
  }, null)
}

export function sortHistoryDesc(history: HistoryEntry[]) {
  return [...history].sort((a, b) => b.start_date.localeCompare(a.start_date) || b.history_id - a.history_id)
}

export function pageOf<T>(items: T[], page: number, size = PAGE_SIZE) {
  const pages = Math.max(1, Math.ceil(items.length / size))
  const current = Math.min(Math.max(1, page), pages)
  return { items: items.slice((current - 1) * size, current * size), page: current, pages }
}

export type EmploymentForm = {
  name: string
  birth_date: string
  gender: "" | "M" | "F"
  email: string
  hire_date: string
  dept_no: string
  position_code: string
  phone: string
  extension_no: string
  address: string
  base_salary: string
  role_codes: string[]
  create_account: boolean
  password: string
}

export const emptyEmploymentForm = (hireDate = ""): EmploymentForm => ({
  name: "", birth_date: "", gender: "", email: "", hire_date: hireDate, dept_no: "", position_code: "",
  phone: "", extension_no: "", address: "", base_salary: "", role_codes: [], create_account: false, password: "",
})

export type FieldErrors = Partial<Record<keyof EmploymentForm | "account", string>>

const optional = (value: string) => value.trim() || null
const SALARY_PATTERN = /^\d{1,13}(\.\d{1,2})?$/

// 입력 안내용 사전 검증이다. 이메일 중복·기간 중복 등 업무 규칙은 서버 응답을 따른다(HR-008).
export function validateEmploymentForm(form: EmploymentForm, mode: "create" | "rehire"): FieldErrors {
  const errors: FieldErrors = {}
  if (mode === "create") {
    if (!form.name.trim()) errors.name = "이름을 입력하세요."
    if (!form.birth_date) errors.birth_date = "생년월일을 입력하세요."
    if (!form.gender) errors.gender = "성별을 선택하세요."
  }
  if (!form.email.trim()) errors.email = "사내 이메일을 입력하세요."
  if (!form.hire_date) errors.hire_date = "입사일을 입력하세요."
  if (!form.dept_no) errors.dept_no = "부서를 선택하세요."
  if (!form.position_code) errors.position_code = "직급을 선택하세요."
  if (!SALARY_PATTERN.test(form.base_salary.trim())) errors.base_salary = "기본급은 0 이상의 숫자로 소수 둘째 자리까지 입력하세요."
  if (form.create_account && form.password.length < 8) errors.password = "초기 비밀번호는 8자 이상이어야 합니다."
  return errors
}

export function toNewHirePayload(form: EmploymentForm): NewHirePayload {
  return {
    name: form.name.trim(),
    birth_date: form.birth_date,
    gender: form.gender as "M" | "F",
    ...employmentTerms(form),
  }
}

// 재입사는 입력한 인적사항만 보내 기존 Person 값을 유지한다.
export function toRehirePayload(form: EmploymentForm): RehirePayload {
  return {
    ...(form.name.trim() ? { name: form.name.trim() } : {}),
    ...(form.birth_date ? { birth_date: form.birth_date } : {}),
    ...(form.gender ? { gender: form.gender } : {}),
    ...employmentTerms(form),
  }
}

function employmentTerms(form: EmploymentForm) {
  return {
    email: form.email.trim(),
    hire_date: form.hire_date,
    dept_no: Number(form.dept_no),
    position_code: form.position_code,
    phone: optional(form.phone),
    extension_no: optional(form.extension_no),
    address: optional(form.address),
    base_salary: form.base_salary.trim(),
    role_codes: form.role_codes,
    account: form.create_account ? { password: form.password } : null,
  }
}

export function isSalary(value: string) {
  return SALARY_PATTERN.test(value.trim())
}

// 서버 필드 오류를 첫 메시지 기준으로 화면 필드에 연결한다. 중첩 account 오류는 password로 표시한다.
export function firstFieldErrors(fieldErrors: Record<string, string[]>) {
  const result: Record<string, string> = {}
  for (const [key, messages] of Object.entries(fieldErrors)) {
    if (messages[0]) result[key === "account" ? "password" : key] = messages[0]
  }
  return result
}
