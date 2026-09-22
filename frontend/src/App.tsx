import { FormEvent, useCallback, useEffect, useMemo, useState } from "react"

import { getCurrentUser, loginWithEmail, logoutSession } from "./api/auth"
import { ApiError, requestJson } from "./api/client"
import { ConnectionStatus } from "./components/ConnectionStatus"
import { LoginPanel } from "./components/LoginPanel"
import { PayrollPanel } from "./components/PayrollPanel"
import { WorkforcePanel } from "./components/WorkforcePanel"
import { environment } from "./config/environment"
import type { CurrentUser } from "./types/auth"
import type { SystemHealth } from "./types/health"

type VacationStatus = "대기" | "승인" | "반려" | "취소" | "회수"
type VacationType = { type_id: string; type_name: string; is_paid: boolean; deduct_days: string }
type VacationRequest = {
  request_id: number
  employee_no: number
  type_id: string
  start_datetime: string
  end_datetime: string
  use_days: string
  status: VacationStatus
  approver_no: number
  approved_at: string | null
  reject_reason: string | null
  request_reason: string | null
}

const employees = [
  { no: 1001, label: "김사원 · 신청자" },
  { no: 1002, label: "이사원 · 신청자" },
  { no: 2001, label: "박부장 · 승인자" },
  { no: 9001, label: "최인사 · 인사관리자" },
]
const initialForm = { type_id: "ANNUAL", start_datetime: "", end_datetime: "", use_days: "1.00", reason: "" }

type VacationAppProps = {
  currentUser: CurrentUser | null
  onSessionExpired: () => void
  onLogout: () => Promise<void>
}

function VacationApp({ currentUser, onSessionExpired, onLogout }: VacationAppProps) {
  const [employeeNo, setEmployeeNo] = useState(1001)
  const [types, setTypes] = useState<VacationType[]>([])
  const [mine, setMine] = useState<VacationRequest[]>([])
  const [approvals, setApprovals] = useState<VacationRequest[]>([])
  const [tab, setTab] = useState<"mine" | "approvals">("mine")
  const [module, setModule] = useState<"vacation" | "workforce" | "payroll">("vacation")
  const [form, setForm] = useState(initialForm)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(false)
  const [health, setHealth] = useState<SystemHealth | null>(null)
  const [checkingConnection, setCheckingConnection] = useState(false)
  const [connectionMessage, setConnectionMessage] = useState("")
  const [simulatedOffline, setSimulatedOffline] = useState(environment.startsOffline)
  const connected = !simulatedOffline && health?.end_to_end.status === "connected"
  const developmentIdentity = environment.authMode === "development"
  const identityEmployeeNo = developmentIdentity
    ? employeeNo
    : currentUser?.employee?.emp_no ?? 0

  const headers = useMemo(() => {
    const value: Record<string, string> = { "Content-Type": "application/json" }
    if (developmentIdentity) value["X-Employee-No"] = String(identityEmployeeNo)
    return value
  }, [developmentIdentity, identityEmployeeNo])

  const api = useCallback(async <T,>(path: string, options?: RequestInit): Promise<T> => {
    return requestJson<T>(`/api/vacations/${path}`, {
      ...options,
      headers: { ...headers, ...options?.headers },
    })
  }, [headers])

  const checkConnection = useCallback(async () => {
    if (simulatedOffline) {
      setHealth(null)
      setConnectionMessage("개발용 강제 오프라인 상태입니다.")
      return
    }

    setCheckingConnection(true)
    try {
      const result = await requestJson<SystemHealth>("/api/health/")
      setHealth(result)
      setConnectionMessage(
        result.end_to_end.status === "connected"
          ? "백엔드와 의존 서비스가 정상 연결되었습니다."
          : "일부 서비스가 연결되지 않았습니다.",
      )
    } catch (error) {
      setHealth(null)
      setConnectionMessage(error instanceof Error ? error.message : "연결 상태를 확인하지 못했습니다.")
    } finally {
      setCheckingConnection(false)
    }
  }, [simulatedOffline])

  const refresh = useCallback(async () => {
    if (!connected) return
    setLoading(true)
    try {
      const [typeData, mineData, approvalData] = await Promise.all([
        api<VacationType[]>("types/"), api<VacationRequest[]>("requests/"), api<VacationRequest[]>("approvals/"),
      ])
      setTypes(typeData)
      setMine(mineData)
      setApprovals(approvalData)
      setMessage("")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "데이터를 불러오지 못했습니다.")
      if (error instanceof ApiError && error.unavailable) void checkConnection()
      if (
        error instanceof ApiError
        && environment.authMode === "session"
        && (error.status === 401 || error.status === 403)
      ) onSessionExpired()
    } finally {
      setLoading(false)
    }
  }, [api, checkConnection, connected, onSessionExpired])

  useEffect(() => {
    const timer = window.setTimeout(() => void checkConnection(), 0)
    const interval = window.setInterval(() => void checkConnection(), environment.healthPollIntervalMs)
    return () => {
      window.clearTimeout(timer)
      window.clearInterval(interval)
    }
  }, [checkConnection])

  useEffect(() => {
    if (!connected) return
    const timer = window.setTimeout(() => void refresh(), 0)
    return () => window.clearTimeout(timer)
  }, [connected, identityEmployeeNo, refresh])

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!connected) return
    setLoading(true)
    try {
      const payload = { ...form, start_datetime: new Date(form.start_datetime).toISOString(), end_datetime: new Date(form.end_datetime).toISOString() }
      if (editingId) await api(`requests/${editingId}/resubmit/`, { method: "PUT", body: JSON.stringify(payload) })
      else await api("requests/", { method: "POST", body: JSON.stringify(payload) })
      const wasEditing = editingId !== null
      setForm(initialForm)
      setEditingId(null)
      await refresh()
      setMessage(wasEditing ? "수정한 휴가를 다시 신청했습니다." : "휴가를 신청했습니다.")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "신청하지 못했습니다.")
    } finally { setLoading(false) }
  }

  async function runAction(id: number, action: string, needsReason = false) {
    if (!connected) return
    const reason = needsReason ? window.prompt("처리 사유를 입력하세요.") : null
    if (needsReason && !reason) return
    setLoading(true)
    try {
      await api(`requests/${id}/${action}/`, { method: "POST", body: needsReason ? JSON.stringify({ reason }) : undefined })
      await refresh()
      setMessage("처리가 완료되었습니다.")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "처리하지 못했습니다.")
    } finally { setLoading(false) }
  }

  function beginResubmit(item: VacationRequest) {
    const local = (value: string) => new Date(value).toISOString().slice(0, 16)
    setEditingId(item.request_id)
    setForm({ type_id: item.type_id, start_datetime: local(item.start_datetime), end_datetime: local(item.end_datetime), use_days: item.use_days, reason: item.request_reason ?? "" })
    window.scrollTo({ top: 0, behavior: "smooth" })
  }

  const visible = connected ? tab === "mine" ? mine : approvals : []
  const mineCount = connected ? mine.length : 0
  const approvalCount = connected ? approvals.length : 0
  return (
    <main className="shell">
      <header className="topbar">
        <div><p className="eyebrow">ERP · VACATION</p><h1>휴가 신청과 승인</h1><p className="lede">신청부터 승인, 회수와 재신청까지 하나의 흐름으로 관리합니다.</p></div>
        {developmentIdentity
          ? <label className="employee-picker"><span>개발용 현재 사용자</span><select value={employeeNo} onChange={(event) => setEmployeeNo(Number(event.target.value))}>{employees.map((employee) => <option key={employee.no} value={employee.no}>{employee.label} ({employee.no})</option>)}</select></label>
          : <div className="user-summary"><span>{currentUser?.employee?.name ?? currentUser?.email}</span><small>{currentUser?.email}</small><button type="button" onClick={() => void onLogout()}>로그아웃</button></div>}
      </header>
      <ConnectionStatus
        health={health}
        checking={checkingConnection}
        message={connectionMessage}
        simulatedOffline={simulatedOffline}
        showDevelopmentControls={environment.connectionTestControls}
        onCheck={() => void checkConnection()}
        onToggleOffline={() => setSimulatedOffline((value) => !value)}
      />
      {!developmentIdentity && (
        <nav className="module-nav" aria-label="업무 모듈">
          <button className={module === "vacation" ? "active" : ""} type="button" onClick={() => setModule("vacation")}>휴가</button>
          <button className={module === "workforce" ? "active" : ""} type="button" onClick={() => setModule("workforce")}>사원·부서</button>
          <button className={module === "payroll" ? "active" : ""} type="button" onClick={() => setModule("payroll")}>급여</button>
        </nav>
      )}
      {message && <div className="notice" role="status">{message}</div>}
      {module === "vacation" && <section className="workspace" aria-disabled={!connected}>
        <form className="request-card" onSubmit={submit}>
          <div className="section-heading"><div><p className="step">01</p><h2>{editingId ? "휴가 수정·재신청" : "새 휴가 신청"}</h2></div>{editingId && <button className="text-button" type="button" onClick={() => { setEditingId(null); setForm(initialForm) }}>취소</button>}</div>
          <label>휴가 유형<select disabled={!connected} value={form.type_id} onChange={(event) => setForm({ ...form, type_id: event.target.value })}>{types.map((type) => <option key={type.type_id} value={type.type_id}>{type.type_name}</option>)}</select></label>
          <div className="two-columns">
            <label>시작일시<input disabled={!connected} required type="datetime-local" value={form.start_datetime} onChange={(event) => setForm({ ...form, start_datetime: event.target.value })} /></label>
            <label>종료일시<input disabled={!connected} required type="datetime-local" value={form.end_datetime} onChange={(event) => setForm({ ...form, end_datetime: event.target.value })} /></label>
          </div>
          <label>차감일수<input disabled={!connected} required min="0.01" step="0.5" type="number" value={form.use_days} onChange={(event) => setForm({ ...form, use_days: event.target.value })} /></label>
          <label>신청 사유<textarea disabled={!connected} rows={4} placeholder="업무 인수인계 등 필요한 내용을 적어주세요." value={form.reason} onChange={(event) => setForm({ ...form, reason: event.target.value })} /></label>
          <button className="primary" disabled={loading || !connected} type="submit">{connected ? editingId ? "다시 신청하기" : "승인 요청하기" : "오프라인 / 미연결"}</button>
          <p className="helper">{connected ? "연차는 현재 환경의 잔여일수 기준으로 검증되며, 승인자는 자동 지정됩니다." : "End to end 연결이 정상화되면 업무 기능이 활성화됩니다."}</p>
        </form>
        <section className="list-panel">
          <div className="section-heading"><div><p className="step">02</p><h2>휴가 현황</h2></div><button className="refresh" type="button" onClick={() => void refresh()} disabled={loading || !connected}>새로고침</button></div>
          <div className="tabs" role="tablist"><button className={tab === "mine" ? "active" : ""} onClick={() => setTab("mine")} type="button">내 신청 <b>{mineCount}</b></button><button className={tab === "approvals" ? "active" : ""} onClick={() => setTab("approvals")} type="button">승인 대상 <b>{approvalCount}</b></button></div>
          <div className="request-list">
            {visible.length === 0 && <div className="empty">{connected ? "표시할 휴가 신청이 없습니다." : "서버 연결 후 휴가 현황을 불러옵니다."}</div>}
            {visible.map((item) => <article className="request-item" key={item.request_id}>
              <div className="item-top"><div><span className={`badge badge--${item.status}`}>{item.status}</span><strong>{types.find((type) => type.type_id === item.type_id)?.type_name ?? item.type_id}</strong></div><span className="request-id">#{item.request_id}</span></div>
              <p className="period">{new Date(item.start_datetime).toLocaleString("ko-KR")} <span>→</span> {new Date(item.end_datetime).toLocaleString("ko-KR")}</p>
              <dl><div><dt>신청자</dt><dd>{item.employee_no}</dd></div><div><dt>승인자</dt><dd>{item.approver_no}</dd></div><div><dt>차감</dt><dd>{item.use_days}일</dd></div></dl>
              {item.request_reason && <p className="reason">{item.request_reason}</p>}{item.reject_reason && <p className="reject-reason">반려 사유 · {item.reject_reason}</p>}
              <div className="actions">
                {tab === "mine" && item.status === "대기" && <button onClick={() => void runAction(item.request_id, "cancel")} type="button">신청 취소</button>}
                {tab === "mine" && item.status === "회수" && <button className="accent" onClick={() => beginResubmit(item)} type="button">수정·재신청</button>}
                {tab === "approvals" && item.status === "대기" && <><button className="accent" onClick={() => void runAction(item.request_id, "approve")} type="button">승인</button><button onClick={() => void runAction(item.request_id, "reject", true)} type="button">반려</button></>}
                {tab === "approvals" && item.status === "승인" && <button onClick={() => void runAction(item.request_id, "recall", true)} type="button">승인 회수</button>}
              </div>
            </article>)}
          </div>
        </section>
      </section>}
      {module === "workforce" && currentUser && (
        <WorkforcePanel enabled={connected} currentUser={currentUser} />
      )}
      {module === "payroll" && currentUser && (
        <PayrollPanel enabled={connected} currentUser={currentUser} />
      )}
    </main>
  )
}

function App() {
  const [currentUser, setCurrentUser] = useState<CurrentUser | null | undefined>(
    environment.authMode === "development" ? null : undefined,
  )
  const [authLoading, setAuthLoading] = useState(false)
  const [authError, setAuthError] = useState("")
  const handleSessionExpired = useCallback(() => setCurrentUser(null), [])

  useEffect(() => {
    if (environment.authMode === "development") return
    let active = true
    void getCurrentUser()
      .then((user) => {
        if (active) setCurrentUser(user)
      })
      .catch(() => {
        if (active) setCurrentUser(null)
      })
    return () => { active = false }
  }, [])

  async function handleLogin(email: string, password: string) {
    setAuthLoading(true)
    setAuthError("")
    try {
      setCurrentUser(await loginWithEmail(email, password))
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "로그인하지 못했습니다.")
    } finally {
      setAuthLoading(false)
    }
  }

  async function handleLogout() {
    try {
      await logoutSession()
    } finally {
      setCurrentUser(null)
    }
  }

  if (environment.authMode === "session" && currentUser === undefined) {
    return <main className="login-shell"><p>인증 상태를 확인하고 있습니다.</p></main>
  }
  if (environment.authMode === "session" && currentUser === null) {
    return <LoginPanel loading={authLoading} error={authError} onLogin={handleLogin} />
  }

  return (
    <VacationApp
      currentUser={currentUser ?? null}
      onSessionExpired={handleSessionExpired}
      onLogout={handleLogout}
    />
  )
}

export default App
