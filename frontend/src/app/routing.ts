import type { LucideIcon } from "lucide-react"

export type ModuleRegistration = {
  id: string
  label: string
  icon: LucideIcon
  entry: string
  // 지정하면 이 역할이 활성인 사용자에게만 메뉴를 보이고 화면을 연다. 서버 권한 검사는 별도로 유지한다.
  requiredRole?: string
  allowSuperuser?: boolean
  screens: { id: string; title: string; icon: LucideIcon; menu?: boolean }[]
}

export type Route = { moduleId: string; screenId: string; search?: string }
export const defaultRoute: Route = { moduleId: "vacation", screenId: "leave-apply" }

export function routeHref(route: Route) {
  const query = route.search ? new URLSearchParams(route.search).toString() : ""
  return `#/${encodeURIComponent(route.moduleId)}/${encodeURIComponent(route.screenId)}${query ? `?${query}` : ""}`
}

export function parseRoute(hash: string): Route | null {
  if (!hash || hash === "#" || hash === "#/") return defaultRoute
  const match = /^#\/([a-z][a-z-]*)\/([a-z][a-z-]*)(?:\?([^#]*))?$/.exec(hash)
  return match ? { moduleId: match[1], screenId: match[2], ...(match[3] ? { search: match[3] } : {}) } : null
}

export function findScreen(route: Route | null, modules: ModuleRegistration[]) {
  const module = modules.find((item) => item.id === route?.moduleId)
  const screen = module?.screens.find((item) => item.id === route?.screenId)
  return module && screen ? { module, screen } : null
}
