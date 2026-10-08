import { FormEvent, useCallback, useEffect, useMemo, useState } from "react"

import {
  cancelConfirmation,
  cancelExclusion,
  confirmEvaluation,
  createEvaluation,
  excludeEvaluation,
  getEvaluation,
  getEvaluationHistory,
  listEvaluations,
  listEvaluatorCandidates,
  reassignEvaluation,
  returnEvaluation,
  reviseEvaluation,
  submitEvaluation,
} from "../api/evaluation"
import { loadWorkforce } from "../api/workforce"
import type { CurrentUser } from "../types/auth"
import type {
  Evaluation,
  EvaluationAction,
  EvaluationHistoryEntry,
  EvaluatorCandidate,
} from "../types/evaluation"
import type { DepartmentSummary, EmployeeSummary } from "../types/workforce"

type EvaluationPanelProps = {
  enabled: boolean
  currentUser: CurrentUser
}

const ACTION_LABELS: Record<EvaluationAction, string> = {
  CREATE: "작성",
  REVISE: "수정",
  SUBMIT: "제출",
  RETURN: "반려",
  REASSIGN: "평가자 재배정",
  CONFIRM: "확정",
  CANCEL_CONFIRMATION: "확정 취소",
  EXCLUDE: "평가 제외",
  CANCEL_EXCLUSION: "제외 취소",
}

const EDITABLE = ["작성중", "반려"]
const UNCONFIRMED = ["작성중", "제출", "반려"]
const MINIMUM_TENURE_MONTHS = 3

function isoDate(value: Date) {
  const month = String(value.getMonth() + 1).padStart(2, "0")
  const day = String(value.getDate()).padStart(2, "0")
  return `${value.getFullYear()}-${month}-${day}`
}

// Mirrors the backend rule for the picker only: year end for past years, today for this year.
function basisDate(year: string) {
  const today = isoDate(new Date())
  const yearEnd = `${year}-12-31`
  return yearEnd < today ? yearEnd : today
}

function addMonths(isoValue: string, months: number) {
  const [year, month, day] = isoValue.split("-").map(Number)
  const target = new Date(year, month - 1 + months, 1)
  const lastDay = new Date(target.getFullYear(), target.getMonth() + 1, 0).getDate()
  target.setDate(Math.min(day, lastDay))
  return isoDate(target)
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback
}

export function EvaluationPanel({ enabled, currentUser }: EvaluationPanelProps) {
  const myNo = currentUser.employee?.emp_no ?? 0
  // Only guides the UI; the backend enforces every rule.
  const isHRManager = currentUser.roles.includes("HR_MANAGER")
  const currentYear = new Date().getFullYear()
  const yearOptions = [String(currentYear), String(currentYear - 1)]

  const [evaluations, setEvaluations] = useState<Evaluation[]>([])
  const [yearFilter, setYearFilter] = useState("")
  const [selected, setSelected] = useState<Evaluation | null>(null)
  const [history, setHistory] = useState<EvaluationHistoryEntry[]>([])
  const [candidates, setCandidates] = useState<EvaluatorCandidate[]>([])
  const [employees, setEmployees] = useState<EmployeeSummary[]>([])
  const [departments, setDepartments] = useState<DepartmentSummary[]>([])
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(false)

  const [createForm, setCreateForm] = useState({
    emp_no: "",
    eval_year: yearOptions[0],
    score: "",
    comments: "",
  })
  const [editForm, setEditForm] = useState({ score: "", comments: "" })
  const [reason, setReason] = useState("")
  const [newEvaluatorNo, setNewEvaluatorNo] = useState("")

  const refresh = useCallback(async () => {
    if (!enabled) return
    setLoading(true)
    try {
      const [items, workforce] = await Promise.all([
        listEvaluations(yearFilter || undefined),
        loadWorkforce(),
      ])
      setEvaluations(items)
      setEmployees(workforce.employees)
      setDepartments(workforce.departments)
      if (isHRManager) setCandidates(await listEvaluatorCandidates())
      setMessage("")
    } catch (error) {
      setMessage(errorMessage(error, "인사평가를 불러오지 못했습니다."))
    } finally {
      setLoading(false)
    }
  }, [enabled, isHRManager, yearFilter])

  useEffect(() => {
    if (!enabled) return
    const timer = window.setTimeout(() => void refresh(), 0)
    return () => window.clearTimeout(timer)
  }, [enabled, refresh])

  async function open(evalId: number) {
    setLoading(true)
    try {
      const detail = await getEvaluation(evalId)
      setSelected(detail)
      setEditForm({ score: detail.score, comments: detail.comments })
      setReason("")
      setNewEvaluatorNo("")
      // History is only for the current evaluator and HR; others simply see none.
      setHistory(await getEvaluationHistory(evalId).catch(() => []))
    } catch (error) {
      setMessage(errorMessage(error, "평가를 불러오지 못했습니다."))
    } finally {
      setLoading(false)
    }
  }

  async function run(action: () => Promise<Evaluation>, done: string) {
    setLoading(true)
    try {
      const updated = await action()
      setMessage(done)
      await refresh()
      await open(updated.eval_id)
    } catch (error) {
      setMessage(errorMessage(error, "처리하지 못했습니다."))
      setLoading(false)
    }
  }

  function requireReason(action: (text: string) => Promise<Evaluation>, done: string) {
    const text = reason.trim()
    if (!text) {
      setMessage("처리 사유를 입력하세요.")
      return
    }
    void run(() => action(text), done)
  }

  async function submitCreate(event: FormEvent) {
    event.preventDefault()
    await run(
      () => createEvaluation({ ...createForm, emp_no: Number(createForm.emp_no) }),
      "평가를 작성했습니다.",
    )
    setCreateForm({ emp_no: "", eval_year: yearOptions[0], score: "", comments: "" })
  }

  // Employees this user may evaluate as a department head (FN-EV-001), for the picker only.
  const evaluableEmployees = useMemo(() => {
    const headed = departments.filter((department) => department.head_emp_no === myNo)
    const headedNos = new Set(headed.map((department) => department.dept_no))
    const members = employees.filter(
      (employee) => employee.dept_no !== null
        && headedNos.has(employee.dept_no)
        && employee.emp_no !== myNo,
    )
    const childHeads = departments
      .filter((department) => department.parent_dept_no !== null
        && headedNos.has(department.parent_dept_no)
        && department.head_emp_no !== null
        && department.head_emp_no !== myNo)
      .map((department) => employees.find((employee) => employee.emp_no === department.head_emp_no))
      .filter((employee): employee is EmployeeSummary => employee !== undefined)
    const unique = new Map([...members, ...childHeads].map((employee) => [employee.emp_no, employee]))
    const basis = basisDate(createForm.eval_year)
    return [...unique.values()].filter((employee) => employee.tenure_status !== "퇴사"
      // 3개월 이하 근무자는 평가 대상이 아니다.
      && addMonths(employee.hire_date, MINIMUM_TENURE_MONTHS) < basis)
  }, [createForm.eval_year, departments, employees, myNo])

  // A department head who is also an HR manager evaluates; another HR manager confirms.
  const isEvaluator = selected !== null && selected.evaluator_no === myNo
  const canHandleAsHR = selected !== null && isHRManager && selected.emp_no !== myNo
  const reassignOptions = candidates.filter(
    (candidate) => selected !== null
      && candidate.emp_no !== selected.evaluator_no
      && candidate.emp_no !== selected.emp_no,
  )

  return (
    <section className="evaluation-panel">
      {message && <div className="notice" role="status">{message}</div>}
      <div className="workforce-toolbar">
        <div><p className="step">EVALUATION</p><h2>인사평가</h2></div>
        <label>
          평가 연도
          <select value={yearFilter} onChange={(event) => setYearFilter(event.target.value)}>
            <option value="">전체</option>
            {[...yearOptions, String(currentYear - 2)].map((year) => (
              <option key={year} value={year}>{year}</option>
            ))}
          </select>
        </label>
        <button className="refresh" type="button" disabled={loading || !enabled} onClick={() => void refresh()}>새로고침</button>
      </div>

      <div className="workspace">
        <div className="evaluation-side">
          {evaluableEmployees.length > 0 && (
            <form className="request-card" onSubmit={submitCreate}>
              <div className="section-heading"><div><p className="step">01</p><h2>평가 작성</h2></div></div>
              <label>
                평가 대상
                <select required value={createForm.emp_no} onChange={(event) => setCreateForm({ ...createForm, emp_no: event.target.value })}>
                  <option value="">선택하세요</option>
                  {evaluableEmployees.map((employee) => (
                    <option key={employee.emp_no} value={employee.emp_no}>{employee.name} ({employee.emp_no})</option>
                  ))}
                </select>
              </label>
              <div className="two-columns">
                <label>
                  평가 연도
                  <select value={createForm.eval_year} onChange={(event) => setCreateForm({ ...createForm, eval_year: event.target.value })}>
                    {yearOptions.map((year) => <option key={year} value={year}>{year}</option>)}
                  </select>
                </label>
                <label>
                  점수 (0~100)
                  <input required type="number" min="0" max="100" step="0.01" value={createForm.score} onChange={(event) => setCreateForm({ ...createForm, score: event.target.value })} />
                </label>
              </div>
              <label>
                평가 의견
                <textarea rows={4} value={createForm.comments} onChange={(event) => setCreateForm({ ...createForm, comments: event.target.value })} />
              </label>
              <button className="primary" disabled={loading || !enabled} type="submit">작성중으로 저장</button>
              <p className="helper">등급은 점수로 자동 계산됩니다. S 90점 이상, A 80점 이상, B 70점 이상, C 70점 미만. 근무 3개월 이하 사원은 목록에 나오지 않습니다.</p>
            </form>
          )}

          <section className="list-panel">
            <div className="section-heading"><div><p className="step">{evaluableEmployees.length > 0 ? "02" : "01"}</p><h2>평가 목록</h2></div></div>
            <div className="request-list evaluation-list">
              {evaluations.length === 0 && <div className="empty">{enabled ? "표시할 평가가 없습니다." : "서버 연결 후 평가를 불러옵니다."}</div>}
              {evaluations.map((item) => (
                <button
                  key={item.eval_id}
                  type="button"
                  className={`request-item evaluation-item${selected?.eval_id === item.eval_id ? " selected" : ""}`}
                  onClick={() => void open(item.eval_id)}
                >
                  <span className="item-top">
                    <span><span className={`badge badge--${item.eval_status}`}>{item.eval_status}</span> <strong>{item.employee_name ?? item.emp_no}</strong></span>
                    <span className="request-id">{item.eval_year} · #{item.eval_id}</span>
                  </span>
                  <span className="evaluation-meta">평가자 {item.evaluator_name ?? item.evaluator_no} · {item.score}점 · {item.grade}</span>
                </button>
              ))}
            </div>
          </section>
        </div>

        <section className="list-panel" aria-live="polite">
          {!selected && <div className="empty">목록에서 평가를 선택하세요.</div>}
          {selected && (
            <div className="evaluation-detail">
              <div className="section-heading">
                <div><p className="step">{selected.eval_year} · #{selected.eval_id}</p><h2>{selected.employee_name ?? selected.emp_no} 평가</h2></div>
                <span className={`badge badge--${selected.eval_status}`}>{selected.eval_status}</span>
              </div>
              <dl className="evaluation-facts">
                <div><dt>점수</dt><dd>{selected.score}</dd></div>
                <div><dt>등급</dt><dd>{selected.grade}</dd></div>
                <div><dt>현재 평가자</dt><dd>{selected.evaluator_name ?? selected.evaluator_no}</dd></div>
                <div><dt>기준 부서</dt><dd>{selected.snapshot_dept_no ?? "-"}</dd></div>
              </dl>
              {selected.comments && <p className="reason">{selected.comments}</p>}

              {isEvaluator && EDITABLE.includes(selected.eval_status) && (
                <form
                  className="evaluation-form"
                  onSubmit={(event) => {
                    event.preventDefault()
                    void run(() => reviseEvaluation(selected.eval_id, editForm), "평가를 저장했습니다.")
                  }}
                >
                  <h3>평가 수정</h3>
                  <label>
                    점수 (0~100)
                    <input required type="number" min="0" max="100" step="0.01" value={editForm.score} onChange={(event) => setEditForm({ ...editForm, score: event.target.value })} />
                  </label>
                  <label>
                    평가 의견
                    <textarea rows={4} value={editForm.comments} onChange={(event) => setEditForm({ ...editForm, comments: event.target.value })} />
                  </label>
                  <div className="actions">
                    <button type="submit" disabled={loading}>저장</button>
                    <button className="accent" type="button" disabled={loading} onClick={() => void run(() => submitEvaluation(selected.eval_id), "평가를 제출했습니다.")}>제출</button>
                  </div>
                </form>
              )}

              {canHandleAsHR && (
                <div className="evaluation-form">
                  <h3>인사관리자 처리</h3>
                  <label>
                    처리 사유
                    <textarea rows={2} maxLength={255} placeholder="반려·재배정·제외·확정 취소에 필요합니다." value={reason} onChange={(event) => setReason(event.target.value)} />
                  </label>
                  <div className="actions">
                    {selected.eval_status === "제출" && (
                      <>
                        <button type="button" disabled={loading} onClick={() => requireReason((text) => returnEvaluation(selected.eval_id, text), "평가를 반려했습니다.")}>반려</button>
                        {selected.evaluator_no !== myNo && (
                          <button className="accent" type="button" disabled={loading} onClick={() => void run(() => confirmEvaluation(selected.eval_id), "평가를 확정했습니다.")}>확정</button>
                        )}
                      </>
                    )}
                    {selected.eval_status === "확정" && (
                      <button type="button" disabled={loading} onClick={() => requireReason((text) => cancelConfirmation(selected.eval_id, text), "확정을 취소했습니다.")}>확정 취소</button>
                    )}
                    {UNCONFIRMED.includes(selected.eval_status) && (
                      <button type="button" disabled={loading} onClick={() => requireReason((text) => excludeEvaluation(selected.eval_id, text), "평가에서 제외했습니다.")}>평가 제외</button>
                    )}
                    {selected.eval_status === "제외" && (
                      <button type="button" disabled={loading} onClick={() => void run(() => cancelExclusion(selected.eval_id, reason.trim()), "제외를 취소했습니다.")}>제외 취소</button>
                    )}
                  </div>

                  {UNCONFIRMED.includes(selected.eval_status) && (
                    <form
                      className="reassign-form"
                      onSubmit={(event) => {
                        event.preventDefault()
                        requireReason((text) => reassignEvaluation(selected.eval_id, Number(newEvaluatorNo), text), "평가자를 재배정했습니다.")
                      }}
                    >
                      <label>
                        새 평가자 (부서장)
                        <select required value={newEvaluatorNo} onChange={(event) => setNewEvaluatorNo(event.target.value)}>
                          <option value="">부서장을 선택하세요</option>
                          {reassignOptions.map((candidate) => (
                            <option key={`${candidate.emp_no}-${candidate.dept_no}`} value={candidate.emp_no}>
                              {candidate.name} ({candidate.emp_no}) · {candidate.dept_name}
                            </option>
                          ))}
                        </select>
                      </label>
                      <button className="primary" type="submit" disabled={loading || !newEvaluatorNo}>평가자 재배정</button>
                      <p className="helper">재직 중인 현재 부서장만 지정할 수 있습니다. 제출된 평가는 작성중으로 돌아가 새 평가자가 확인 후 다시 제출합니다.</p>
                    </form>
                  )}
                </div>
              )}

              {history.length > 0 && (
                <div className="evaluation-history">
                  <h3>처리 이력</h3>
                  <ol>
                    {history.map((entry) => (
                      <li key={entry.history_id}>
                        <strong>{ACTION_LABELS[entry.action]}</strong>
                        <span>{entry.actor_name ?? entry.actor_no} · {new Date(entry.changed_at).toLocaleString("ko-KR")}</span>
                        {entry.action === "REASSIGN" && <small>평가자 {entry.from_evaluator_no} → {entry.to_evaluator_no}</small>}
                        {entry.reason && <small>사유 · {entry.reason}</small>}
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </section>
  )
}
