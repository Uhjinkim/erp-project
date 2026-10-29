import { ApiError } from "../../api/client"
import { getVacationHistory, listMyVacations, listVacationApprovals, listVacationTypes } from "../../api/vacation"
import type { VacationHistory, VacationRequest, VacationType } from "../../types/vacation"

export type VacationData = {
  types: VacationType[]
  mine: VacationRequest[]
  approvals: VacationRequest[]
  history: VacationHistory[]
  errors: Partial<Record<"types" | "mine" | "approvals" | "history", Error>>
}

export type VacationDataSource = {
  types: typeof listVacationTypes
  mine: typeof listMyVacations
  approvals: typeof listVacationApprovals
  history: typeof getVacationHistory
}
const source: VacationDataSource = { types: listVacationTypes, mine: listMyVacations, approvals: listVacationApprovals, history: getVacationHistory }

export function emptyData(): VacationData {
  return { types: [], mine: [], approvals: [], history: [], errors: {} }
}

export async function loadVacationData(employeeNo: number, screen: string, requestId: number | null, api = source) {
  const data = emptyData()
  const jobs: Promise<void>[] = []
  function load<K extends keyof VacationData["errors"]>(key: K, request: Promise<VacationData[K]>) {
    jobs.push(request.then((result) => { data[key] = result }).catch((error: unknown) => {
      data.errors[key] = error instanceof Error ? error : new Error("데이터를 불러오지 못했습니다.")
    }))
  }
  load("types", api.types(employeeNo, screen === "leave-apply" || screen === "leave-resubmit"))
  if (screen === "leave-mine" || screen === "leave-resubmit" || screen === "leave-detail") load("mine", api.mine(employeeNo))
  if (screen === "leave-queue" || screen === "leave-approve" || screen === "leave-recall" || screen === "leave-detail") load("approvals", api.approvals(employeeNo))
  if (screen === "leave-detail" && requestId) load("history", api.history(employeeNo, requestId))
  await Promise.all(jobs)
  return data
}

export function failureTitle(error: Error) {
  if (error instanceof ApiError && error.status === 403) return "접근 권한이 없습니다"
  if (error instanceof ApiError && error.status === 404) return "신청을 찾을 수 없습니다"
  return "휴가 정보를 불러오지 못했습니다"
}
