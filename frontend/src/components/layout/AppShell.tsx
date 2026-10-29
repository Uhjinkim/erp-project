import { LogOut, Menu, Search } from "lucide-react"
import { useEffect, useId, useState } from "react"
import type { ReactNode } from "react"
import { visibleModules } from "../../app/modules"
import { findScreen, routeHref } from "../../app/routing"
import type { Route } from "../../app/routing"
import type { CurrentUser } from "../../types/auth"
import { Button } from "../ui"
import styles from "./AppShell.module.css"

export function AppShell({ route, user, pending, onLogout, children }: { route: Route | null; user: CurrentUser | null; pending: boolean; onLogout: () => void; children: ReactNode }) {
  const [search, setSearch] = useState("")
  const searchId = useId()
  const [menuOpen, setMenuOpen] = useState(false)
  const modules = visibleModules(user)
  const current = findScreen(route, modules)
  const activeModule = modules.find((module) => module.id === route?.moduleId)
  const screens = activeModule?.screens.filter((screen) => screen.menu !== false && screen.title.includes(search)) ?? []
  useEffect(() => {
    document.title = `${current?.screen.title ?? "화면 찾기"} · WORKLY ERP`
    document.getElementById("page-heading")?.focus()
  }, [current?.screen.id, current?.screen.title])
  return <div className={styles.shell}>
    <a href="#main-content" className={styles.skip} onClick={(event) => { event.preventDefault(); document.getElementById("main-content")?.focus() }}>본문으로 건너뛰기</a>
    <header className={styles.topbar}>
      <a className={styles.brand} href={routeHref({ moduleId: "profile", screenId: "my-profile" })}><span>W</span>WORKLY ERP</a>
      <div className={styles.user}><Button className={styles.mobileMenu} variant="ghost" aria-expanded={menuOpen} aria-controls="screen-menu" onClick={() => setMenuOpen(!menuOpen)}><Menu size={16} aria-hidden="true" />화면 메뉴</Button>
        <span>{user?.employee?.name ?? user?.email ?? "개발용 사원 식별 모드"}</span>
        {user && <Button variant="ghost" size="small" pending={pending} onClick={onLogout}><LogOut size={16} aria-hidden="true" />로그아웃</Button>}
      </div>
    </header>
    <div className={styles.layout}>
      <nav className={styles.rail} aria-label="업무 모듈">{modules.map((module) => {
        const Icon = module.icon
        return <a key={module.id} href={routeHref({ moduleId: module.id, screenId: module.entry })} title={module.label} aria-label={module.label} aria-current={route?.moduleId === module.id ? "true" : undefined} onClick={() => { setSearch(""); setMenuOpen(false) }}><Icon size={24} aria-hidden="true" /></a>
      })}</nav>
      <aside id="screen-menu" className={`${styles.sidebar} ${menuOpen ? styles.sidebarOpen : ""}`}>
        <div className={styles.menuSearch} role="search" aria-label="현재 모듈 메뉴">
          <label className={styles.searchLabel} htmlFor={searchId}>메뉴 검색</label>
          <Search size={16} aria-hidden="true" />
          <input id={searchId} type="search" placeholder="메뉴 검색" autoComplete="off" spellCheck={false} value={search} onChange={(event) => setSearch(event.target.value)} />
        </div>
        <h2>{activeModule?.label ?? "화면 찾기"}</h2>
        <nav className={styles.menu} aria-label="모듈 화면">{screens.map((screen) => {
          const Icon = screen.icon
          return <a key={screen.id} href={routeHref({ moduleId: activeModule!.id, screenId: screen.id })} aria-current={route?.screenId === screen.id ? "page" : undefined} onClick={() => setMenuOpen(false)}><Icon size={18} aria-hidden="true" /><span>{screen.title}</span></a>
        })}{screens.length === 0 && <p>일치하는 화면이 없습니다.</p>}</nav>
      </aside>
      <main id="main-content" tabIndex={-1} className={styles.main}>{children}</main>
    </div>
  </div>
}
