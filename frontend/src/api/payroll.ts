import { requestJson } from "./client"
import type { PayrollComponent, PayrollHistoryEntry, PayrollItem, PayrollStatement } from "../types/payroll"

const jsonHeaders = { "Content-Type": "application/json" }

export async function loadPayrollComponents(): Promise<PayrollComponent[]> {
  return requestJson<PayrollComponent[]>("/api/payroll/components/")
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

export async function createPayrollStatement(
  empNo: number,
  year: number,
  month: number,
  items: Pick<PayrollItem, "component_code" | "amount">[] = [],
): Promise<PayrollStatement> {
  return requestJson<PayrollStatement>("/api/payroll/statements/", {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify({ emp_no: empNo, year, month, items }),
  })
}

export async function updatePayrollItems(
  statementId: number,
  items: Pick<PayrollItem, "component_code" | "amount">[],
): Promise<PayrollStatement> {
  return requestJson<PayrollStatement>(`/api/payroll/statements/${statementId}/items/`, {
    method: "PUT",
    headers: jsonHeaders,
    body: JSON.stringify({ items }),
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
