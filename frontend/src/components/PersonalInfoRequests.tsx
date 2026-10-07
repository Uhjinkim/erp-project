import { FormEvent, useCallback, useEffect, useState } from "react"

import {
  createChangeRequest,
  listChangeRequests,
  processChangeRequest,
  updateMyContact,
} from "../api/workforce"
import type {
  ApprovalRequiredValues,
  EmployeeDetail,
  PersonalInfoChangeRequest,
} from "../types/workforce"

const fieldLabels: Record<keyof ApprovalRequiredValues, string> = {
  email: "사내 이메일",
  bank_code: "은행 코드",
  account_no: "급여계좌",
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback
}

function formatDateTime(value: string | null) {
  return value ? new Date(value).toLocaleString("ko-KR") : "-"
}

function ChangeSummary({ request }: { request: PersonalInfoChangeRequest }) {
  return (
    <ul className="change-summary">
      {request.changed_fields.map((field) => (
        <li key={field}>
          <span>{fieldLabels[field]}</span>
          {request.previous[field] ?? "미등록"} → <strong>{request.requested[field]}</strong>
        </li>
      ))}
    </ul>
  )
}

type PersonalInfoEditorProps = {
  employee: EmployeeDetail
  reloadKey: number
  onContactUpdated: (employee: EmployeeDetail) => void
  onRequestsChanged: () => void
}

/** HR-002: 연락처·주소는 직접 수정하고, 사내 이메일·급여계좌는 변경 요청을 제출한다. */
export function PersonalInfoEditor({
  employee,
  reloadKey,
  onContactUpdated,
  onRequestsChanged,
}: PersonalInfoEditorProps) {
  const [phone, setPhone] = useState(employee.phone ?? "")
  const [address, setAddress] = useState(employee.address ?? "")
  const [email, setEmail] = useState("")
  const [bankCode, setBankCode] = useState("")
  const [accountNo, setAccountNo] = useState("")
  const [requests, setRequests] = useState<PersonalInfoChangeRequest[]>([])
  const [message, setMessage] = useState("")
  const [busy, setBusy] = useState(false)

  const loadRequests = useCallback(async () => {
    try {
      setRequests(await listChangeRequests({ mine: true }))
    } catch (error) {
      setMessage(errorMessage(error, "변경 요청 내역을 불러오지 못했습니다."))
    }
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => void loadRequests(), 0)
    return () => window.clearTimeout(timer)
  }, [loadRequests, reloadKey])

  async function run(action: () => Promise<void>, fallback: string) {
    setBusy(true)
    try {
      await action()
    } catch (error) {
      setMessage(errorMessage(error, fallback))
    } finally {
      setBusy(false)
    }
  }

  function submitContact(event: FormEvent) {
    event.preventDefault()
    void run(async () => {
      const updated = await updateMyContact({ phone: phone.trim() || null, address: address.trim() || null })
      onContactUpdated(updated)
      setMessage("연락처·주소를 수정했습니다.")
    }, "연락처·주소를 수정하지 못했습니다.")
  }

  function submitRequest(event: FormEvent) {
    event.preventDefault()
    const values: Partial<ApprovalRequiredValues> = {}
    if (email.trim()) values.email = email.trim()
    if (bankCode.trim()) values.bank_code = bankCode.trim()
    if (accountNo.trim()) values.account_no = accountNo.trim()
    void run(async () => {
      await createChangeRequest(values)
      setEmail("")
      setBankCode("")
      setAccountNo("")
      onRequestsChanged()
      setMessage("변경 요청을 제출했습니다. 승인 후 반영됩니다.")
    }, "변경 요청을 제출하지 못했습니다.")
  }

  function cancelRequest(requestId: number) {
    void run(async () => {
      await processChangeRequest(requestId, "cancel")
      onRequestsChanged()
      setMessage("변경 요청을 취소했습니다.")
    }, "변경 요청을 취소하지 못했습니다.")
  }

  return (
    <section className="list-panel personal-info-editor">
      <p className="step">MY INFO</p>
      <h2>개인정보 변경</h2>
      {message && <div className="notice" role="status">{message}</div>}
      <div className="personal-info-forms">
        <form onSubmit={submitContact}>
          <h3>연락처·주소 직접 수정</h3>
          <label>연락처<input maxLength={20} value={phone} onChange={(event) => setPhone(event.target.value)} /></label>
          <label>주소<input maxLength={255} value={address} onChange={(event) => setAddress(event.target.value)} /></label>
          <button className="primary" disabled={busy} type="submit">저장</button>
        </form>
        <form onSubmit={submitRequest}>
          <h3>사내 이메일·급여계좌 변경 요청</h3>
          <label>새 사내 이메일<input type="email" maxLength={100} placeholder={employee.email ?? ""} value={email} onChange={(event) => setEmail(event.target.value)} /></label>
          <div className="two-columns">
            <label>새 은행 코드<input maxLength={20} placeholder={employee.bank_code ?? ""} value={bankCode} onChange={(event) => setBankCode(event.target.value)} /></label>
            <label>새 급여계좌<input maxLength={100} placeholder={employee.account_no ?? ""} value={accountNo} onChange={(event) => setAccountNo(event.target.value)} /></label>
          </div>
          <button className="primary" disabled={busy} type="submit">변경 요청</button>
          <p className="helper">승인되면 반영됩니다. 급여계좌는 은행 코드와 함께 입력하세요.</p>
        </form>
      </div>
      <h3>내 변경 요청 <b>{requests.length}</b></h3>
      <div className="change-request-list">
        {requests.map((request) => (
          <article className="change-request-item" key={request.request_id}>
            <div><strong>{request.status}</strong><span>{formatDateTime(request.requested_at)}</span></div>
            <ChangeSummary request={request} />
            {request.reject_reason && <p className="reject-reason">반려 사유: {request.reject_reason}</p>}
            {request.status === "대기" && (
              <div className="actions">
                <button type="button" disabled={busy} onClick={() => cancelRequest(request.request_id)}>요청 취소</button>
              </div>
            )}
          </article>
        ))}
        {requests.length === 0 && <div className="empty">변경 요청 내역이 없습니다.</div>}
      </div>
    </section>
  )
}

type ChangeRequestApprovalsProps = {
  alwaysVisible: boolean
  reloadKey: number
  onProcessed: () => void
}

/**
 * FN-HR-004: 현재 사용자가 처리할 수 있는 대기 요청을 승인·반려한다.
 * 인사관리자 본인의 요청은 상급자(부서장)가 처리하므로 인사관리자가 아니어도 목록이 보일 수 있다.
 */
export function ChangeRequestApprovals({ alwaysVisible, reloadKey, onProcessed }: ChangeRequestApprovalsProps) {
  const [requests, setRequests] = useState<PersonalInfoChangeRequest[]>([])
  const [reasons, setReasons] = useState<Record<number, string>>({})
  const [message, setMessage] = useState("")
  const [busy, setBusy] = useState(false)

  const loadRequests = useCallback(async () => {
    try {
      setRequests(await listChangeRequests({ processable: true }))
    } catch (error) {
      setMessage(errorMessage(error, "변경 요청을 불러오지 못했습니다."))
    }
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => void loadRequests(), 0)
    return () => window.clearTimeout(timer)
  }, [loadRequests, reloadKey])

  async function process(requestId: number, action: "approve" | "reject") {
    setBusy(true)
    try {
      await processChangeRequest(requestId, action, action === "reject" ? reasons[requestId] : undefined)
      onProcessed()
      setMessage(action === "approve" ? "변경 요청을 승인했습니다." : "변경 요청을 반려했습니다.")
    } catch (error) {
      setMessage(errorMessage(error, "변경 요청을 처리하지 못했습니다."))
    } finally {
      setBusy(false)
    }
  }

  if (!alwaysVisible && requests.length === 0 && !message) return null

  return (
    <section className="list-panel">
      <p className="step">APPROVAL</p>
      <h2>개인정보 변경 승인 <b>{requests.length}</b></h2>
      {message && <div className="notice" role="status">{message}</div>}
      <div className="change-request-list">
        {requests.map((request) => (
          <article className="change-request-item" key={request.request_id}>
            <div><strong>사번 #{request.emp_no}</strong><span>{formatDateTime(request.requested_at)}</span></div>
            <ChangeSummary request={request} />
            <label>반려 사유 (선택)
              <input
                maxLength={500}
                value={reasons[request.request_id] ?? ""}
                onChange={(event) => setReasons({ ...reasons, [request.request_id]: event.target.value })}
              />
            </label>
            <div className="actions">
              <button type="button" disabled={busy} onClick={() => void process(request.request_id, "reject")}>반려</button>
              <button className="accent" type="button" disabled={busy} onClick={() => void process(request.request_id, "approve")}>승인</button>
            </div>
          </article>
        ))}
        {requests.length === 0 && <div className="empty">대기 중인 변경 요청이 없습니다.</div>}
      </div>
    </section>
  )
}
