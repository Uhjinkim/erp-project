import { FormEvent, useCallback, useEffect, useMemo, useState } from "react"

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

function App() {
  const [employeeNo, setEmployeeNo] = useState(1001)
  const [types, setTypes] = useState<VacationType[]>([])
  const [mine, setMine] = useState<VacationRequest[]>([])
  const [approvals, setApprovals] = useState<VacationRequest[]>([])
  const [tab, setTab] = useState<"mine" | "approvals">("mine")
  const [form, setForm] = useState(initialForm)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(false)
  const headers = useMemo(() => ({ "Content-Type": "application/json", "X-Employee-No": String(employeeNo) }), [employeeNo])

  const api = useCallback(async <T,>(path: string, options?: RequestInit): Promise<T> => {
    const response = await fetch(`/api/vacations/${path}`, { ...options, headers: { ...headers, ...options?.headers } })
    if (!response.ok) {
      const error = await response.json().catch(() => ({})) as { detail?: string }
      throw new Error(error.detail ?? "요청을 처리하지 못했습니다.")
    }
    return response.json() as Promise<T>
  }, [headers])

  const refresh = useCallback(async () => {
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
    } finally { setLoading(false) }
  }, [api])

  useEffect(() => {
    const timer = window.setTimeout(() => void refresh(), 0)
    return () => window.clearTimeout(timer)
  }, [refresh])

  async function submit(event: FormEvent) {
    event.preventDefault()
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

  const visible = tab === "mine" ? mine : approvals
  return (
    <main className="shell">
      <header className="topbar">
        <div><p className="eyebrow">ERP · VACATION</p><h1>휴가 신청과 승인</h1><p className="lede">신청부터 승인, 회수와 재신청까지 하나의 흐름으로 관리합니다.</p></div>
        <label className="employee-picker"><span>현재 사용자</span><select value={employeeNo} onChange={(event) => setEmployeeNo(Number(event.target.value))}>{employees.map((employee) => <option key={employee.no} value={employee.no}>{employee.label} ({employee.no})</option>)}</select></label>
      </header>
      {message && <div className="notice" role="status">{message}</div>}
      <section className="workspace">
        <form className="request-card" onSubmit={submit}>
          <div className="section-heading"><div><p className="step">01</p><h2>{editingId ? "휴가 수정·재신청" : "새 휴가 신청"}</h2></div>{editingId && <button className="text-button" type="button" onClick={() => { setEditingId(null); setForm(initialForm) }}>취소</button>}</div>
          <label>휴가 유형<select value={form.type_id} onChange={(event) => setForm({ ...form, type_id: event.target.value })}>{types.map((type) => <option key={type.type_id} value={type.type_id}>{type.type_name}</option>)}</select></label>
          <div className="two-columns">
            <label>시작일시<input required type="datetime-local" value={form.start_datetime} onChange={(event) => setForm({ ...form, start_datetime: event.target.value })} /></label>
            <label>종료일시<input required type="datetime-local" value={form.end_datetime} onChange={(event) => setForm({ ...form, end_datetime: event.target.value })} /></label>
          </div>
          <label>차감일수<input required min="0.01" step="0.5" type="number" value={form.use_days} onChange={(event) => setForm({ ...form, use_days: event.target.value })} /></label>
          <label>신청 사유<textarea rows={4} placeholder="업무 인수인계 등 필요한 내용을 적어주세요." value={form.reason} onChange={(event) => setForm({ ...form, reason: event.target.value })} /></label>
          <button className="primary" disabled={loading} type="submit">{editingId ? "다시 신청하기" : "승인 요청하기"}</button>
          <p className="helper">연차는 개발용 잔여일수 기준으로 검증되며, 승인자는 자동 지정됩니다.</p>
        </form>
        <section className="list-panel">
          <div className="section-heading"><div><p className="step">02</p><h2>휴가 현황</h2></div><button className="refresh" type="button" onClick={() => void refresh()} disabled={loading}>새로고침</button></div>
          <div className="tabs" role="tablist"><button className={tab === "mine" ? "active" : ""} onClick={() => setTab("mine")} type="button">내 신청 <b>{mine.length}</b></button><button className={tab === "approvals" ? "active" : ""} onClick={() => setTab("approvals")} type="button">승인 대상 <b>{approvals.length}</b></button></div>
          <div className="request-list">
            {visible.length === 0 && <div className="empty">표시할 휴가 신청이 없습니다.</div>}
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
      </section>
    </main>
  )
}

export default App
