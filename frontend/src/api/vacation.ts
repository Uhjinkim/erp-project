import { requestJson } from "./client"
import { environment } from "../config/environment"
import type { VacationAction, VacationHistory, VacationInput, VacationRequest, VacationType } from "../types/vacation"

export function requestVacation<T>(path: string, employeeNo: number, options: RequestInit = {}) {
  const headers = new Headers(options.headers)
  headers.set("Content-Type", "application/json")
  if (environment.authMode === "development") headers.set("X-Employee-No", String(employeeNo))
  return requestJson<T>(`/api/vacations/${path}`, { ...options, headers })
}

export async function listVacationTypes(employeeNo: number, includeBalance = false) {
  const types = await requestVacation<VacationType[]>(includeBalance ? "types/?include_balance=true" : "types/", employeeNo)
  if (includeBalance && types.some((type) => type.remaining_days === undefined)) {
    throw new Error("서버 응답에 잔여일수가 없습니다. 백엔드에 최신 변경이 반영되었는지 확인해 주세요.")
  }
  return types
}

export const listMyVacations = (employeeNo: number) =>
  requestVacation<VacationRequest[]>("requests/", employeeNo)

export const listVacationApprovals = (employeeNo: number) =>
  requestVacation<VacationRequest[]>("approvals/", employeeNo)

export const getVacationHistory = (employeeNo: number, requestId: number) =>
  requestVacation<VacationHistory[]>(`requests/${requestId}/history/`, employeeNo)

export const createVacation = (employeeNo: number, input: VacationInput) =>
  requestVacation<VacationRequest>("requests/", employeeNo, { method: "POST", body: JSON.stringify(input) })

export const resubmitVacation = (employeeNo: number, requestId: number, input: VacationInput) =>
  requestVacation<VacationRequest>(`requests/${requestId}/resubmit/`, employeeNo, { method: "PUT", body: JSON.stringify(input) })

export const changeVacationStatus = (employeeNo: number, requestId: number, action: VacationAction, reason?: string) =>
  requestVacation<VacationRequest>(`requests/${requestId}/${action}/`, employeeNo, {
    method: "POST",
    body: action === "reject" || action === "recall" ? JSON.stringify({ reason: reason?.trim() }) : undefined,
  })
