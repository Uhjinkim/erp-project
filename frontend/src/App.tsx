import { AppShell } from "./components/layout/AppShell"
import { Alert, EmptyState, ErrorState, PageHeader, Spinner } from "./components/ui"
import { LoginPanel } from "./components/LoginPanel"
import { modules, visibleModules } from "./app/modules"
import { findScreen, routeHref, defaultRoute } from "./app/routing"
import { useRoute } from "./app/useRoute"
import { useSession } from "./app/useSession"
import { ModuleScreen } from "./app/ModuleScreen"

function Workspace({ session }: { session: ReturnType<typeof useSession> }) {
  const route = useRoute()
  // 권한이 없어 숨긴 모듈은 주소로 직접 들어와도 등록되지 않은 화면으로 처리한다.
  const available = visibleModules(session.user)
  const current = findScreen(route, available)
  const restricted = !current && findScreen(route, modules)
  const returnModule = available.find((module) => module.id === route?.moduleId)
  const returnRoute = returnModule ? { moduleId: returnModule.id, screenId: returnModule.entry } : { moduleId: "profile", screenId: "my-profile" }
  return <AppShell route={route} user={session.user} pending={session.pending} onLogout={() => void session.logout()}>
    <PageHeader title={current?.screen.title ?? (restricted ? "접근 권한이 없는 화면입니다" : "화면을 찾을 수 없습니다")} description={current?.module.label} />
    {session.error && <Alert tone="error">{session.error}</Alert>}
    {current ? <ModuleScreen key={`${session.user?.id ?? "development"}:${current.module.id}:${current.screen.id}`} route={route!} user={session.user} /> : restricted ? <EmptyState title="담당자 권한이 필요합니다" action={<a href={routeHref(returnRoute)}>이용 가능한 화면으로 이동</a>}>현재 계정의 메뉴에서 업무를 선택하세요.</EmptyState> : <EmptyState title="등록되지 않은 화면입니다" action={<a href={routeHref(defaultRoute)}>휴가 화면으로 이동</a>}>주소를 확인하거나 왼쪽 메뉴에서 화면을 선택하세요.</EmptyState>}
  </AppShell>
}

function AuthenticatedApp() {
  const session = useSession()
  if (session.status === "checking") return <main><Spinner label="인증 상태를 확인하고 있습니다" /></main>
  if (session.status === "unavailable") return <main><ErrorState title="인증 서버에 연결할 수 없습니다" onRetry={session.retry}>연결을확인한 뒤 다시 시도하세요.</ErrorState></main>
  if (session.status === "anonymous" || session.status === "expired") {
    return <LoginPanel loading={session.pending} error={session.error} onLogin={session.login} expired={session.status === "expired"} />
  }
  return <Workspace key={session.user?.id ?? "development"} session={session} />
}

export default function App() {
  return <AuthenticatedApp />
}
