import { AppShell } from "./components/layout/AppShell"
import { Alert, EmptyState, ErrorState, PageHeader, Spinner } from "./components/ui"
import { LoginPanel } from "./components/LoginPanel"
import { ConnectionStatus } from "./components/ConnectionStatus"
import { modules } from "./app/modules"
import { findScreen, routeHref, defaultRoute } from "./app/routing"
import { useRoute } from "./app/useRoute"
import { useSession } from "./app/useSession"
import { useConnection } from "./app/useConnection"
import { ModuleScreen } from "./app/ModuleScreen"
import { UiGallery } from "./features/design-system/UiGallery"
import { environment } from "./config/environment"

function Workspace({ session }: { session: ReturnType<typeof useSession> }) {
  const route = useRoute()
  const connection = useConnection()
  const current = findScreen(route, modules)
  return <AppShell route={route} user={session.user} pending={session.pending} onLogout={() => void session.logout()}>
    <PageHeader title={current?.screen.title ?? "화면을 찾을 수 없습니다"} description={current?.module.label} />
    {session.error && <Alert tone="error">{session.error}</Alert>}
    {!connection.backendConnected && <Alert tone="warning">{connection.message || "서비스 연결을 확인하고 있습니다."} 업무 데이터는 연결 후 불러옵니다.</Alert>}
    {current ? <ModuleScreen key={`${session.user?.id ?? "development"}:${current.module.id}:${current.screen.id}`} route={route!} user={session.user} connection={connection} /> : <EmptyState title="등록되지 않은 화면입니다" action={<a href={routeHref(defaultRoute)}>휴가 화면으로 이동</a>}>주소를 확인하거나 왼쪽 메뉴에서 화면을 선택하세요.</EmptyState>}
    <details><summary>서비스 연결 상태</summary><ConnectionStatus health={connection.health} checking={connection.checking} message={connection.message} simulatedOffline={connection.simulatedOffline} showDevelopmentControls={environment.connectionTestControls} onCheck={() => void connection.check()} onToggleOffline={connection.toggleOffline} /></details>
    {environment.isDevelopment && <a href="#/design-system/gallery">공통 컴포넌트 전시</a>}
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
  const route = useRoute()
  if (environment.isDevelopment && route?.moduleId === "design-system" && route.screenId === "gallery") {
    return <><PageHeader title="디자인시스템" description="개발 전용 · 합성 예시" /><UiGallery /><a href={routeHref(defaultRoute)}>업무 화면으로 이동</a></>
  }
  return <AuthenticatedApp />
}
