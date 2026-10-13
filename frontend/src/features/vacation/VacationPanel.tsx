import { FormEvent, useCallback, useEffect, useRef, useState } from "react"

import { Alert, Badge, Button, Card, DetailList, EmptyState, Modal, Select, Spinner, Tabs, Textarea, TextInput } from "../../components/ui"
import { ApiError } from "../../api/client"
import styles from "./vacation.module.css"
import { requestVacation } from "../../api/vacation"
import { environment } from "../../config/environment"
import type { CurrentUser } from "../../types/auth"
import type { VacationType, VacationRequest } from "../../types/vacation"

const employees = [
  { no: 1001, label: "김사원 · 신청자" },
  { no: 1002, label: "이사원 · 신청자" },
  { no: 2001, label: "박부장 · 승인자" },
  { no: 9001, label: "최인사 · 인사관리자" },
]
const initialForm = { type_id: "ANNUAL", start_datetime: "", end_datetime: "", use_days: "1.00", reason: "" }

type VacationPanelProps = {
  currentUser: CurrentUser | null
  connected: boolean
}

export function VacationPanel({ currentUser, connected }: VacationPanelProps) {
  const [employeeNo, setEmployeeNo] = useState(1001)
  const identity = environment.authMode === "development" ? employeeNo : currentUser?.employee?.emp_no ?? 0
  return <div className={styles.stack}>
    {environment.authMode === "development" && <Select label="개발용 현재 사용자" value={employeeNo} onChange={(event) => setEmployeeNo(Number(event.target.value))}>{employees.map((employee) => <option key={employee.no} value={employee.no}>{employee.label} ({employee.no})</option>)}</Select>}
    <VacationWorkspace key={identity} employeeNo={identity} connected={connected} />
  </div>
}

function VacationWorkspace({ employeeNo, connected }: { employeeNo: number; connected: boolean }) {
  const [types, setTypes] = useState<VacationType[]>([])
  const [mine, setMine] = useState<VacationRequest[]>([])
  const [approvals, setApprovals] = useState<VacationRequest[]>([])
  const [tab, setTab] = useState<"mine" | "approvals">("mine")
  const [form, setForm] = useState(initialForm)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(false)
  const [action, setAction] = useState<{ id: number; name: string } | null>(null)
  const [reason, setReason] = useState("")
  const [errors, setErrors] = useState<Record<string, string[]>>({})
  const generation = useRef(0)
  const busy = useRef(false)
  const api = useCallback(<T,>(path: string, options?: RequestInit) =>
    requestVacation<T>(path, employeeNo, options), [employeeNo])

  const refresh = useCallback(async () => {
    if (!connected) return
    const run = ++generation.current
    setLoading(true)
    try {
      const [typeData, mineData, approvalData] = await Promise.all([
        api<VacationType[]>("types/"), api<VacationRequest[]>("requests/"), api<VacationRequest[]>("approvals/"),
      ])
      if (run !== generation.current) return
      setTypes(typeData)
      setMine(mineData)
      setApprovals(approvalData)
      setMessage("")
    } catch (error) {
      if (run === generation.current) setMessage(error instanceof Error ? error.message : "데이터를 불러오지 못했습니다.")
    } finally {
      if (run === generation.current) setLoading(false)
    }
  }, [api, connected])

  useEffect(() => {
    const counter = generation
    if (!connected) return
    const timer = window.setTimeout(() => void refresh(), 0)
    return () => { counter.current++; window.clearTimeout(timer) }
  }, [connected, refresh])

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!connected || busy.current) return
    busy.current = true
    setLoading(true)
    setErrors({})
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
      if (error instanceof ApiError) setErrors(error.fieldErrors)
      setMessage(error instanceof Error ? error.message : "신청하지 못했습니다.")
    } finally { busy.current = false; setLoading(false) }
  }

  async function runAction(id: number, name: string, needsReason = false) {
    if (!connected || busy.current) return
    if (needsReason && action?.id !== id) {
      setReason("")
      setAction({ id, name })
      return
    }
    if (needsReason && !reason.trim()) return
    busy.current = true
    setLoading(true)
    try {
      await api(`requests/${id}/${name}/`, { method: "POST", body: needsReason ? JSON.stringify({ reason: reason.trim() }) : undefined })
      await refresh()
      setAction(null)
      setMessage("처리가 완료되었습니다.")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "처리하지 못했습니다.")
    } finally { busy.current = false; setLoading(false) }
  }

  function beginResubmit(item: VacationRequest) {
    const local = (value: string) => {
      const date = new Date(value)
      return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 16)
    }
    setEditingId(item.request_id)
    setForm({ type_id: item.type_id, start_datetime: local(item.start_datetime), end_datetime: local(item.end_datetime), use_days: item.use_days, reason: item.request_reason ?? "" })
    document.getElementById("page-heading")?.scrollIntoView({ behavior: "smooth" })
  }

  const visible = connected ? tab === "mine" ? mine : approvals : []
  return <>
    {message && <Alert>{message}</Alert>}
    <div className={styles.workspace}>
      <Card title={editingId ? "휴가 수정·재신청" : "새 휴가 신청"}>
        <form className={styles.stack} onSubmit={submit}>
          <Select label="휴가 유형" disabled={!connected || loading} value={form.type_id} error={errors.type_id?.[0]} onChange={(event) => setForm({ ...form, type_id: event.target.value })}>{types.map((type) => <option key={type.type_id} value={type.type_id}>{type.type_name}</option>)}</Select>
          <TextInput label="시작일시" disabled={!connected || loading} required type="datetime-local" value={form.start_datetime} error={errors.start_datetime?.[0]} onChange={(event) => setForm({ ...form, start_datetime: event.target.value })} />
          <TextInput label="종료일시" disabled={!connected || loading} required type="datetime-local" value={form.end_datetime} error={errors.end_datetime?.[0]} onChange={(event) => setForm({ ...form, end_datetime: event.target.value })} />
          <TextInput label="차감일수" disabled={!connected || loading} required min="0.01" step="0.5" type="number" value={form.use_days} error={errors.use_days?.[0]} onChange={(event) => setForm({ ...form, use_days: event.target.value })} />
          <Textarea label="신청 사유" disabled={!connected || loading} rows={4} value={form.reason} error={errors.reason?.[0]} onChange={(event) => setForm({ ...form, reason: event.target.value })} />
          <Button pending={loading} disabled={!connected} type="submit">{editingId ? "다시 신청하기" : "승인 요청하기"}</Button>
          {editingId && <Button variant="secondary" disabled={loading} onClick={() => { setEditingId(null); setForm(initialForm); setErrors({}) }}>편집 취소</Button>}
          <p className={styles.hint}>잔여일수와 승인자는 서버에서 검증합니다.</p>
        </form>
      </Card>
      <Card title="휴가 현황" actions={<Button variant="ghost" size="small" onClick={() => void refresh()} disabled={loading || !connected}>새로고침</Button>}>
        <Tabs label="휴가 목록" items={[{ value: "mine", label: `내 신청 ${connected ? mine.length : 0}` }, { value: "approvals", label: `승인 대상 ${connected ? approvals.length : 0}` }]} value={tab} onChange={(value) => setTab(value as "mine" | "approvals")}>
          <div className={styles.stack}>
            {loading && <Spinner />}
            {!loading && visible.length === 0 && <EmptyState title={connected ? "표시할 휴가 신청이 없습니다" : "서버 연결 후 목록을 불러옵니다"} />}
            {visible.map((item) => <article key={item.request_id} className={styles.request}>
              <div className={styles.row}><Badge tone={item.status === "승인" ? "success" : item.status === "반려" ? "error" : "warning"}>{item.status}</Badge><strong>{types.find((type) => type.type_id === item.type_id)?.type_name ?? item.type_id}</strong><span>#{item.request_id}</span></div>
              <p>{new Date(item.start_datetime).toLocaleString("ko-KR")} → {new Date(item.end_datetime).toLocaleString("ko-KR")}</p>
              <DetailList items={[{ key: "employee", label: "신청자", value: item.employee_no }, { key: "approver", label: "승인자", value: item.approver_no }, { key: "days", label: "차감", value: `${item.use_days}일` }]} />
              {item.request_reason && <p>{item.request_reason}</p>}{item.reject_reason && <Alert tone="error">반려 사유 · {item.reject_reason}</Alert>}
              <div className={styles.row}>
                {tab === "mine" && item.status === "대기" && <Button variant="secondary" disabled={loading} onClick={() => void runAction(item.request_id, "cancel")}>신청 취소</Button>}
                {tab === "mine" && item.status === "회수" && <Button disabled={loading} onClick={() => beginResubmit(item)}>수정·재신청</Button>}
                {tab === "approvals" && item.status === "대기" && <><Button disabled={loading} onClick={() => void runAction(item.request_id, "approve")}>승인</Button><Button variant="danger" disabled={loading} onClick={() => void runAction(item.request_id, "reject", true)}>반려</Button></>}
                {tab === "approvals" && item.status === "승인" && <Button variant="danger" disabled={loading} onClick={() => void runAction(item.request_id, "recall", true)}>승인 회수</Button>}
              </div>
            </article>)}
          </div>
        </Tabs>
      </Card>
    </div>
    <Modal open={action !== null} title={action?.name === "reject" ? "휴가 반려" : "승인 휴가 회수"} busy={loading} onClose={() => setAction(null)}>
      <form className={styles.stack} onSubmit={(event) => { event.preventDefault(); if (action) void runAction(action.id, action.name, true) }}>
        <Textarea label="처리 사유" required value={reason} onChange={(event) => setReason(event.target.value)} disabled={loading} />
        {message && <Alert>{message}</Alert>}
        <Button type="submit" variant="danger" pending={loading} disabled={!reason.trim()}>처리하기</Button>
      </form>
    </Modal>
  </>
}
