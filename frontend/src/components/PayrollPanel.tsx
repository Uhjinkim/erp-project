import { FormEvent, useCallback, useEffect, useMemo, useState } from "react"

import {
  cancelPayrollConfirmation,
  confirmPayrollStatement,
  createPayrollStatement,
  loadAllPayrollStatements,
  loadMyPayrollStatements,
  loadPayrollComponents,
  loadPayrollHistory,
  loadPayrollStatementsForEmployee,
  updatePayrollItems,
} from "../api/payroll"
import type { CurrentUser } from "../types/auth"
import type { PayrollComponent, PayrollHistoryEntry, PayrollStatement } from "../types/payroll"

type PayrollPanelProps = {
  enabled: boolean
  currentUser: CurrentUser
}

type ItemDraftRow = { component_code: string; amount: string }

const emptyCreateForm = { empNo: "", year: String(new Date().getFullYear()), month: String(new Date().getMonth() + 1) }

function toItemDrafts(statement: PayrollStatement): ItemDraftRow[] {
  return statement.items.length > 0
    ? statement.items.map((item) => ({ component_code: item.component_code, amount: String(item.amount) }))
    : [{ component_code: "", amount: "" }]
}

export function PayrollPanel({ enabled, currentUser }: PayrollPanelProps) {
  const isPayrollManager = currentUser.is_superuser || currentUser.roles.includes("PAYROLL_MANAGER")
  const [tab, setTab] = useState<"mine" | "manage">("mine")
  const [components, setComponents] = useState<PayrollComponent[]>([])
  const [mine, setMine] = useState<PayrollStatement[]>([])
  const [managed, setManaged] = useState<PayrollStatement[]>([])
  const [empFilter, setEmpFilter] = useState("")
  const [createForm, setCreateForm] = useState(emptyCreateForm)
  const [itemDrafts, setItemDrafts] = useState<Record<number, ItemDraftRow[]>>({})
  const [histories, setHistories] = useState<Record<number, PayrollHistoryEntry[]>>({})
  const [openHistory, setOpenHistory] = useState<number | null>(null)
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(false)

  const visible = tab === "mine" ? mine : managed

  const refresh = useCallback(async () => {
    if (!enabled) return
    setLoading(true)
    try {
      const [componentList, mineList] = await Promise.all([loadPayrollComponents(), loadMyPayrollStatements()])
      setComponents(componentList)
      setMine(mineList)
      if (isPayrollManager) {
        const trimmed = empFilter.trim()
        const managedList = trimmed
          ? await loadPayrollStatementsForEmployee(Number(trimmed))
          : await loadAllPayrollStatements()
        setManaged(managedList)
      }
      setMessage("")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "급여 정보를 불러오지 못했습니다.")
    } finally {
      setLoading(false)
    }
  }, [enabled, empFilter, isPayrollManager])

  useEffect(() => {
    if (!enabled) return
    const timer = window.setTimeout(() => void refresh(), 0)
    return () => window.clearTimeout(timer)
  }, [enabled, refresh])

  const componentName = (code: string) => components.find((item) => item.code === code)?.name ?? code

  async function submitCreate(event: FormEvent) {
    event.preventDefault()
    setLoading(true)
    try {
      await createPayrollStatement(Number(createForm.empNo), Number(createForm.year), Number(createForm.month))
      setCreateForm({ ...emptyCreateForm, year: createForm.year, month: createForm.month })
      await refresh()
      setMessage("급여를 생성했습니다.")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "급여를 생성하지 못했습니다.")
    } finally {
      setLoading(false)
    }
  }

  function beginEditItems(statement: PayrollStatement) {
    setItemDrafts((previous) => ({ ...previous, [statement.statement_id]: toItemDrafts(statement) }))
  }

  function updateDraftRow(statementId: number, index: number, patch: Partial<ItemDraftRow>) {
    setItemDrafts((previous) => {
      const rows = [...(previous[statementId] ?? [])]
      rows[index] = { ...rows[index], ...patch }
      return { ...previous, [statementId]: rows }
    })
  }

  function addDraftRow(statementId: number) {
    setItemDrafts((previous) => ({
      ...previous,
      [statementId]: [...(previous[statementId] ?? []), { component_code: "", amount: "" }],
    }))
  }

  function removeDraftRow(statementId: number, index: number) {
    setItemDrafts((previous) => ({
      ...previous,
      [statementId]: (previous[statementId] ?? []).filter((_, rowIndex) => rowIndex !== index),
    }))
  }

  async function saveItems(statementId: number) {
    const rows = (itemDrafts[statementId] ?? []).filter((row) => row.component_code && row.amount !== "")
    if (rows.length === 0) {
      setMessage("구성항목을 최소 1건 이상 입력해야 합니다.")
      return
    }
    setLoading(true)
    try {
      await updatePayrollItems(
        statementId,
        rows.map((row) => ({ component_code: row.component_code, amount: Number(row.amount) })),
      )
      setItemDrafts((previous) => {
        const next = { ...previous }
        delete next[statementId]
        return next
      })
      await refresh()
      setMessage("급여 구성항목을 저장했습니다.")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "구성항목을 저장하지 못했습니다.")
    } finally {
      setLoading(false)
    }
  }

  async function confirm(statementId: number) {
    setLoading(true)
    try {
      await confirmPayrollStatement(statementId)
      await refresh()
      setMessage("급여를 확정했습니다.")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "확정하지 못했습니다.")
    } finally {
      setLoading(false)
    }
  }

  async function cancelConfirmation(statementId: number) {
    const reason = window.prompt("확정취소 사유를 입력하세요.")
    if (!reason) return
    setLoading(true)
    try {
      await cancelPayrollConfirmation(statementId, reason)
      await refresh()
      setMessage("확정을 취소했습니다.")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "확정취소하지 못했습니다.")
    } finally {
      setLoading(false)
    }
  }

  async function toggleHistory(statementId: number) {
    if (openHistory === statementId) {
      setOpenHistory(null)
      return
    }
    try {
      const entries = await loadPayrollHistory(statementId)
      setHistories((previous) => ({ ...previous, [statementId]: entries }))
      setOpenHistory(statementId)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "이력을 불러오지 못했습니다.")
    }
  }

  const earningComponents = useMemo(() => components.filter((item) => item.category === "지급"), [components])
  const deductionComponents = useMemo(() => components.filter((item) => item.category === "공제"), [components])

  return (
    <section className="payroll-panel">
      {message && <div className="notice" role="status">{message}</div>}
      {isPayrollManager && (
        <div className="tabs" role="tablist">
          <button className={tab === "mine" ? "active" : ""} onClick={() => setTab("mine")} type="button">
            내 급여 <b>{mine.length}</b>
          </button>
          <button className={tab === "manage" ? "active" : ""} onClick={() => setTab("manage")} type="button">
            급여 관리 <b>{managed.length}</b>
          </button>
        </div>
      )}

      {tab === "manage" && isPayrollManager && (
        <>
          <form className="department-form" onSubmit={submitCreate}>
            <h3>급여 생성</h3>
            <div className="two-columns">
              <input
                required
                type="number"
                placeholder="사번"
                value={createForm.empNo}
                onChange={(event) => setCreateForm({ ...createForm, empNo: event.target.value })}
              />
              <input
                required
                type="number"
                min="1"
                max="12"
                placeholder="정산월"
                value={createForm.month}
                onChange={(event) => setCreateForm({ ...createForm, month: event.target.value })}
              />
            </div>
            <input
              required
              type="number"
              placeholder="정산연도"
              value={createForm.year}
              onChange={(event) => setCreateForm({ ...createForm, year: event.target.value })}
            />
            <button className="primary" disabled={loading} type="submit">급여 생성</button>
          </form>
          <div className="workforce-toolbar">
            <div>
              <p className="step">FILTER</p>
              <h3>사번으로 조회</h3>
            </div>
            <input
              aria-label="사번 검색"
              placeholder="비우면 전체 조회"
              value={empFilter}
              onChange={(event) => setEmpFilter(event.target.value)}
            />
            <button className="refresh" type="button" disabled={loading} onClick={() => void refresh()}>새로고침</button>
          </div>
        </>
      )}

      <div className="request-list">
        {visible.length === 0 && <div className="empty">표시할 급여가 없습니다.</div>}
        {visible.map((item) => (
          <article className="request-item" key={item.statement_id}>
            <div className="item-top">
              <div>
                <span className={`badge badge--payroll-${item.status}`}>{item.status}</span>
                <strong>{item.year}년 {item.month}월</strong>
              </div>
              <span className="request-id">#{item.statement_id}</span>
            </div>
            <p className="period">사번 {item.employee_no} <span>·</span> 지급일 {item.payment_date}</p>
            <dl>
              <div><dt>총지급액</dt><dd>{item.total_earnings.toLocaleString("ko-KR")}원</dd></div>
              <div><dt>총공제액</dt><dd>{item.total_deductions.toLocaleString("ko-KR")}원</dd></div>
              <div><dt>실지급액</dt><dd>{item.net_pay.toLocaleString("ko-KR")}원</dd></div>
            </dl>
            <div className="payroll-items">
              {item.items.map((component) => (
                <span className="payroll-item-chip" key={component.item_id ?? component.component_code}>
                  {componentName(component.component_code)} {component.category === "공제" ? "-" : ""}
                  {component.amount.toLocaleString("ko-KR")}원
                </span>
              ))}
            </div>

            {tab === "manage" && isPayrollManager && item.status === "작성중" && !itemDrafts[item.statement_id] && (
              <div className="actions">
                <button onClick={() => beginEditItems(item)} type="button">구성항목 편집</button>
                <button className="accent" onClick={() => void confirm(item.statement_id)} type="button">확정</button>
              </div>
            )}

            {tab === "manage" && isPayrollManager && item.status === "확정" && (
              <div className="actions">
                <button onClick={() => void cancelConfirmation(item.statement_id)} type="button">확정취소</button>
              </div>
            )}

            {itemDrafts[item.statement_id] && (
              <div className="payroll-items-editor">
                {itemDrafts[item.statement_id].map((row, index) => (
                  <div className="payroll-item-row" key={index}>
                    <select
                      value={row.component_code}
                      onChange={(event) =>
                        updateDraftRow(item.statement_id, index, { component_code: event.target.value })
                      }
                    >
                      <option value="">구성항목 선택</option>
                      <optgroup label="지급">
                        {earningComponents.map((component) => (
                          <option key={component.code} value={component.code}>{component.name}</option>
                        ))}
                      </optgroup>
                      <optgroup label="공제">
                        {deductionComponents.map((component) => (
                          <option key={component.code} value={component.code}>{component.name}</option>
                        ))}
                      </optgroup>
                    </select>
                    <input
                      type="number"
                      min="0"
                      placeholder="금액"
                      value={row.amount}
                      onChange={(event) => updateDraftRow(item.statement_id, index, { amount: event.target.value })}
                    />
                    <button type="button" onClick={() => removeDraftRow(item.statement_id, index)}>삭제</button>
                  </div>
                ))}
                <div className="actions">
                  <button type="button" onClick={() => addDraftRow(item.statement_id)}>항목 추가</button>
                  <button
                    type="button"
                    onClick={() =>
                      setItemDrafts((previous) => {
                        const next = { ...previous }
                        delete next[item.statement_id]
                        return next
                      })
                    }
                  >
                    취소
                  </button>
                  <button className="accent" type="button" onClick={() => void saveItems(item.statement_id)}>저장</button>
                </div>
              </div>
            )}

            <div className="actions">
              <button type="button" onClick={() => void toggleHistory(item.statement_id)}>
                {openHistory === item.statement_id ? "이력 닫기" : "이력 보기"}
              </button>
            </div>
            {openHistory === item.statement_id && (
              <ul className="payroll-history">
                {(histories[item.statement_id] ?? []).map((entry) => (
                  <li key={entry.history_id}>
                    <strong>{entry.action}</strong> · {new Date(entry.changed_at).toLocaleString("ko-KR")} · 처리자 {entry.actor_employee_no}
                    {entry.reason && <span> · 사유 {entry.reason}</span>}
                    {entry.change_summary && <span> · {entry.change_summary}</span>}
                  </li>
                ))}
                {(histories[item.statement_id] ?? []).length === 0 && <li>이력이 없습니다.</li>}
              </ul>
            )}
          </article>
        ))}
      </div>
    </section>
  )
}
