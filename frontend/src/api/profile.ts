import { requestJson } from "./client"
import type { EmployeeDetail } from "../types/workforce"
import type { ApprovalRequiredValues, ChangeRequestStatus, PersonalInfoChangeRequest } from "../types/profile"

export async function getMyEmployeeInfo() {
  return requestJson<EmployeeDetail>("/api/workforce/employees/me/")
}

const jsonHeaders = { "Content-Type": "application/json" }
const changeRequestsPath = "/api/workforce/personal-info-requests/"

export async function listChangeRequests(
  options: { status?: ChangeRequestStatus, processable?: boolean, mine?: boolean } = {},
) {
  const params = new URLSearchParams()
  if (options.status) params.set("status", options.status)
  if (options.processable) params.set("processable", "true")
  if (options.mine) params.set("mine", "true")
  const query = params.toString() ? `?${params}` : ""
  return requestJson<PersonalInfoChangeRequest[]>(`${changeRequestsPath}${query}`)
}

export async function createChangeRequest(values: Partial<ApprovalRequiredValues>) {
  return requestJson<PersonalInfoChangeRequest>(changeRequestsPath, {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify(values),
  })
}

export async function processChangeRequest(
  requestId: number,
  action: "approve" | "reject" | "cancel",
  reason?: string,
) {
  return requestJson<PersonalInfoChangeRequest>(`${changeRequestsPath}${requestId}/${action}/`, {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify(reason ? { reason } : {}),
  })
}

export async function getChangeRequest(requestId: number) {
  return requestJson<PersonalInfoChangeRequest>(`${changeRequestsPath}${requestId}/`)
}
