import { ApiError, requestJson } from "./client"
import { environment } from "../config/environment"
import type {
  PayrollComponent,
  PayrollHistoryEntry,
  PayrollItem,
  PayrollStatement,
  PayrollTargetEmployee,
} from "../types/payroll"

const jsonHeaders = { "Content-Type": "application/json" }

type ItemInput = Pick<PayrollItem, "component_code" | "amount">

export async function loadPayrollComponents(): Promise<PayrollComponent[]> {
  return requestJson<PayrollComponent[]>("/api/payroll/components/")
}

// Payroll-manager-only list of whom to pay. The workforce employee list is HR-manager-only (HR-001).
export async function loadPayrollTargets(): Promise<PayrollTargetEmployee[]> {
  return requestJson<PayrollTargetEmployee[]>("/api/payroll/employees/")
}

export async function loadMyPayrollStatements(): Promise<PayrollStatement[]> {
  return requestJson<PayrollStatement[]>("/api/payroll/statements/")
}

export async function loadPayrollStatementsForEmployee(empNo: number): Promise<PayrollStatement[]> {
  return requestJson<PayrollStatement[]>(`/api/payroll/statements/?emp_no=${empNo}`)
}

export async function loadAllPayrollStatements(): Promise<PayrollStatement[]> {
  return requestJson<PayrollStatement[]>("/api/payroll/statements/?all=true")
}

// paymentDate null lets the backend apply the settlement-date policy.
export async function createPayrollStatement(
  empNo: number,
  year: number,
  month: number,
  items: ItemInput[] = [],
  paymentDate: string | null = null,
): Promise<PayrollStatement> {
  return requestJson<PayrollStatement>("/api/payroll/statements/", {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify({ emp_no: empNo, year, month, items, payment_date: paymentDate }),
  })
}

export async function updatePayrollItems(
  statementId: number,
  items: ItemInput[],
  paymentDate: string | null = null,
): Promise<PayrollStatement> {
  return requestJson<PayrollStatement>(`/api/payroll/statements/${statementId}/items/`, {
    method: "PUT",
    headers: jsonHeaders,
    body: JSON.stringify({ items, payment_date: paymentDate }),
  })
}

export async function confirmPayrollStatement(statementId: number): Promise<PayrollStatement> {
  return requestJson<PayrollStatement>(`/api/payroll/statements/${statementId}/confirm/`, {
    method: "POST",
  })
}

export async function cancelPayrollConfirmation(statementId: number, reason: string): Promise<PayrollStatement> {
  return requestJson<PayrollStatement>(`/api/payroll/statements/${statementId}/cancel-confirmation/`, {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify({ reason }),
  })
}

export async function loadPayrollHistory(statementId: number): Promise<PayrollHistoryEntry[]> {
  return requestJson<PayrollHistoryEntry[]>(`/api/payroll/statements/${statementId}/history/`)
}

export async function downloadPayslipExcel(statement: PayrollStatement): Promise<void> {
  let response: Response
  try {
    response = await fetch(
      `${environment.apiBaseUrl}/api/payroll/statements/${statement.statement_id}/excel/`,
      { credentials: "same-origin" },
    )
  } catch {
    throw new ApiError("백엔드 서버에 연결할 수 없습니다.", true)
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new ApiError(body?.detail ?? "급여명세서를 내려받지 못했습니다.", response.status >= 500, response.status)
  }
  const url = URL.createObjectURL(await response.blob())
  const link = document.createElement("a")
  link.href = url
  link.download = `급여명세서_${statement.year}${String(statement.month).padStart(2, "0")}_${statement.employee_no}.xlsx`
  link.click()
  URL.revokeObjectURL(url)
}
