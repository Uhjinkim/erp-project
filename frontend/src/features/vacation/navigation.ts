import { routeHref } from "../../app/routing"

export type VacationHref = (screen: string, requestId?: number, filters?: URLSearchParams) => string

export function vacationNavigation(employeeNo?: number): VacationHref {
  return (screen, requestId, filters) => {
    const query = new URLSearchParams(filters)
    if (employeeNo) query.set("employeeNo", String(employeeNo))
    if (requestId) query.set("requestId", String(requestId))
    return routeHref({ moduleId: "vacation", screenId: screen, search: query.toString() })
  }
}
