import { useCallback, useEffect, useRef, useState } from "react"

import { Alert, Badge, Button, Card, ConfirmDialog, DetailList, EmptyState, ErrorState, Modal, Select, Spinner, Table, Tabs, Textarea } from "../../../components/ui"
import {
  cancelConfirmation,
  cancelExclusion,
  confirmEvaluation,
  excludeEvaluation,
  getEvaluation,
  getEvaluationHistory,
  listEvaluations,
  listEvaluatorCandidates,
  reassignEvaluation,
  returnEvaluation,
} from "../../../api/evaluation"
import type { CurrentUser } from "../../../types/auth"
import type { Evaluation, EvaluationHistoryEntry, EvaluationStatus, EvaluatorCandidate } from "../../../types/evaluation"
import { EvaluationHistory } from "../components/EvaluationHistory"
import { HR_MANAGER_ROLE, STATUSES, STATUS_TONE, UNCONFIRMED, errorText, filterYears, formatDateTime, go, isAuthor } from "../model"
import styles from "../evaluation.module.css"

type ReasonAction = "return" | "cancel-confirmation" | "exclude" | "cancel-exclusion" | "reassign"
const REASON_ACTIONS: Record<ReasonAction, { title: string; label: string; required: boolean; done: string; danger?: boolean }> = {
  return: { title: "평가 반려", label: "반려", required: true, done: "평가를 반려했습니다." },
  "cancel-confirmation": { title: "확정 취소", label: "확정 취소", required: true, done: "확정을 취소했습니다.", danger: true },
  exclude: { title: "평가 제외", label: "평가 제외", required: true, done: "평가에서 제외했습니다.", danger: true },
  "cancel-exclusion": { title: "제외 취소", label: "제외 취소", required: false, done: "제외를 취소했습니다." },
  reassign: { title: "평가자 재배정", label: "재배정", required: true, done: "평가자를 재배정했습니다." },
}

/** evaluation-hr: HR managers review, return, confirm, correct, exclude and reassign (FN-EV-002~004). */
export function HrScreen({ user, enabled, search }: { user: CurrentUser; enabled: boolean; search?: string }) {
  if (!user.roles.includes(HR_MANAGER_ROLE)) {
    return <EmptyState title="인사관리자만 사용할 수 있는 화면입니다">평가 작성은 팀 평가 대상 목록, 내 평가는 내 평가 결과 화면에서 확인하세요.</EmptyState>
  }
  return <HrWorkspace user={user} enabled={enabled} selectedId={Number(new URLSearchParams(search ?? "").get("evalId")) || null} />
}

function HrWorkspace({ user, enabled, selectedId }: { user: CurrentUser; enabled: boolean; selectedId: number | null }) {
  const myNo = user.employee?.emp_no ?? 0
  const [year, setYear] = useState("")
  const [status, setStatus] = useState<"all" | EvaluationStatus>("all")
  const [items, setItems] = useState<Evaluation[]>([])
  const [candidates, setCandidates] = useState<EvaluatorCandidate[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const generation = useRef(0)

  const refresh = useCallback(async () => {
    if (!enabled) return
    const run = ++generation.current
    setLoading(true)
    setError("")
    try {
      const [list, candidateList] = await Promise.all([listEvaluations(year || undefined), listEvaluatorCandidates()])
      if (run !== generation.current) return
      setItems(list)
      setCandidates(candidateList)
    } catch (caught) {
      if (run === generation.current) setError(errorText(caught, "평가 목록을 불러오지 못했습니다."))
    } finally {
      if (run === generation.current) setLoading(false)
    }
  }, [enabled, year])

  useEffect(() => {
    const timer = window.setTimeout(() => void refresh(), 0)
    return () => window.clearTimeout(timer)
  }, [refresh])

  if (error) return <ErrorState onRetry={() => void refresh()}>{error}</ErrorState>

  const visible = status === "all" ? items : items.filter((item) => item.eval_status === status)
  const counts = (value: EvaluationStatus) => items.filter((item) => item.eval_status === value).length
  return <div className={styles.stack}>
    <div className={styles.toolbar}>
      <Select label="평가 연도" value={year} onChange={(event) => setYear(event.target.value)}>
        <option value="">전체</option>
        {filterYears().map((item) => <option key={item} value={item}>{item}</option>)}
      </Select>
      <Button variant="secondary" onClick={() => void refresh()} pending={loading}>새로고침</Button>
    </div>
    <div className={styles.workspace}>
      <Tabs label="평가 상태" value={status} onChange={(value) => setStatus(value as "all" | EvaluationStatus)}
        items={[{ value: "all", label: `전체 ${items.length}` }, ...STATUSES.map((value) => ({ value, label: `${value} ${counts(value)}` }))]}>
        {loading ? <Spinner /> : visible.length === 0 ? <EmptyState title="표시할 평가가 없습니다" /> : <Table caption={`평가 ${visible.length}건`}>
          <thead><tr><th scope="col">대상</th><th scope="col">연도</th><th scope="col">평가자</th><th scope="col">점수·등급</th><th scope="col">상태</th></tr></thead>
          <tbody>{visible.map((item) => <tr key={item.eval_id} className={item.eval_id === selectedId ? styles.selected : undefined}>
            <td><button type="button" className={styles.rowButton} aria-current={item.eval_id === selectedId || undefined} onClick={() => go("evaluation-hr", { evalId: String(item.eval_id) })}>{item.employee_name ?? item.emp_no}</button></td>
            <td>{item.eval_year}</td><td>{item.evaluator_name ?? item.evaluator_no}</td><td>{item.score} · {item.grade}</td>
            <td><Badge tone={STATUS_TONE[item.eval_status]}>{item.eval_status}</Badge></td>
          </tr>)}</tbody>
        </Table>}
      </Tabs>
      {selectedId
        ? <HrDetail key={selectedId} evalId={selectedId} myNo={myNo} enabled={enabled} candidates={candidates} onChanged={() => void refresh()} />
        : <EmptyState title="목록에서 평가를 선택하세요" />}
    </div>
  </div>
}

function HrDetail({ evalId, myNo, enabled, candidates, onChanged }: { evalId: number; myNo: number; enabled: boolean; candidates: EvaluatorCandidate[]; onChanged: () => void }) {
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null)
  const [history, setHistory] = useState<EvaluationHistoryEntry[]>([])
  const [loadError, setLoadError] = useState("")
  const [message, setMessage] = useState<{ tone: "success" | "error"; text: string } | null>(null)
  const [dialog, setDialog] = useState<ReasonAction | "confirm" | null>(null)
  const [reason, setReason] = useState("")
  const [reasonError, setReasonError] = useState("")
  const [newEvaluator, setNewEvaluator] = useState("")
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    if (!enabled) return
    setLoadError("")
    try {
      const detail = await getEvaluation(evalId)
      setEvaluation(detail)
      setHistory(await getEvaluationHistory(evalId).catch(() => []))
    } catch (caught) {
      setLoadError(errorText(caught, "평가를 불러오지 못했습니다."))
    }
  }, [enabled, evalId])

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0)
    return () => window.clearTimeout(timer)
  }, [load])

  function open(next: ReasonAction | "confirm") {
    setReason("")
    setReasonError("")
    setNewEvaluator("")
    setDialog(next)
  }

  async function execute(action: () => Promise<Evaluation>, done: string) {
    if (busy) return
    setBusy(true)
    setMessage(null)
    try {
      await action()
      setMessage({ tone: "success", text: done })
      setDialog(null)
      onChanged()
    } catch (caught) {
      setMessage({ tone: "error", text: errorText(caught, "처리하지 못했습니다.") })
      setDialog(null)
    } finally {
      await load()
      setBusy(false)
    }
  }

  function submitReason(kind: ReasonAction) {
    const text = reason.trim()
    if (REASON_ACTIONS[kind].required && !text) {
      setReasonError("처리 사유를 입력하세요.")
      return
    }
    if (kind === "reassign" && !newEvaluator) {
      setReasonError("새 평가자를 선택하세요.")
      return
    }
    const call = {
      return: () => returnEvaluation(evalId, text),
      "cancel-confirmation": () => cancelConfirmation(evalId, text),
      exclude: () => excludeEvaluation(evalId, text),
      "cancel-exclusion": () => cancelExclusion(evalId, text),
      reassign: () => reassignEvaluation(evalId, Number(newEvaluator), text),
    }[kind]
    void execute(call, REASON_ACTIONS[kind].done)
  }

  if (loadError) return <ErrorState onRetry={() => void load()}>{loadError}</ErrorState>
  if (!evaluation) return <Spinner label="평가를 불러오는 중" />

  const status = evaluation.eval_status
  const author = isAuthor(myNo, evaluation.evaluator_no, history)
  const reassignOptions = candidates.filter((candidate) => candidate.emp_no !== evaluation.evaluator_no && candidate.emp_no !== evaluation.emp_no)
  const reasonDialog = dialog && dialog !== "confirm" ? dialog : null
  return <div className={styles.stack}>
    <Card title={`${evaluation.employee_name ?? evaluation.emp_no} · ${evaluation.eval_year}`} actions={<Badge tone={STATUS_TONE[status]}>{status}</Badge>}>
      <div className={styles.form}>
        {message && <Alert tone={message.tone}>{message.text}</Alert>}
        <DetailList items={[
          { key: "score", label: "점수·등급", value: `${evaluation.score} · ${evaluation.grade}` },
          { key: "evaluator", label: "현재 평가자", value: evaluation.evaluator_name ?? evaluation.evaluator_no },
          { key: "dept", label: "기준 부서", value: evaluation.snapshot_dept_no ?? "-" },
          { key: "confirmed", label: "확정", value: evaluation.confirmed_by ? `${evaluation.confirmed_by} · ${formatDateTime(evaluation.confirmed_at)}` : "-" },
        ]} />
        {evaluation.comments && <p className={styles.comments}>{evaluation.comments}</p>}
        <div className={styles.actions}>
          {status === "제출" && !author && <>
            <Button onClick={() => open("confirm")}>확정</Button>
            <Button variant="secondary" onClick={() => open("return")}>반려</Button>
          </>}
          {UNCONFIRMED.includes(status) && !author && <>
            <Button variant="secondary" onClick={() => open("reassign")}>평가자 재배정</Button>
            <Button variant="danger" onClick={() => open("exclude")}>평가 제외</Button>
          </>}
          {status === "확정" && <Button variant="danger" onClick={() => open("cancel-confirmation")}>확정 취소</Button>}
          {status === "제외" && <Button variant="secondary" onClick={() => open("cancel-exclusion")}>제외 취소</Button>}
        </div>
        {author && UNCONFIRMED.includes(status) && <p className={styles.hint}>직접 작성한 평가는 반려·확정·제외·재배정을 다른 인사관리자가 처리합니다.</p>}
      </div>
    </Card>
    <EvaluationHistory entries={history} />

    <ConfirmDialog open={dialog === "confirm"} title="평가를 확정할까요?" confirmLabel="확정" busy={busy} onClose={() => setDialog(null)} onConfirm={() => void execute(() => confirmEvaluation(evalId), "평가를 확정했습니다.")}>
      <p>확정하면 평가 대상자에게 공개되고, 이후 수정은 확정 취소를 거쳐야 합니다.</p>
    </ConfirmDialog>
    <Modal open={reasonDialog !== null} title={reasonDialog ? REASON_ACTIONS[reasonDialog].title : ""} busy={busy} onClose={() => setDialog(null)}
      actions={reasonDialog && <>
        <Button variant="secondary" disabled={busy} onClick={() => setDialog(null)}>취소</Button>
        <Button variant={REASON_ACTIONS[reasonDialog].danger ? "danger" : "primary"} pending={busy} onClick={() => submitReason(reasonDialog)}>{REASON_ACTIONS[reasonDialog].label}</Button>
      </>}>
      <div className={styles.form}>
        {reasonDialog === "reassign" && <>
          <Select label="새 평가자 (부서장)" required value={newEvaluator} onChange={(event) => setNewEvaluator(event.target.value)}>
            <option value="">부서장을 선택하세요</option>
            {reassignOptions.map((candidate) => <option key={`${candidate.emp_no}-${candidate.dept_no}`} value={candidate.emp_no}>{candidate.name} ({candidate.emp_no}) · {candidate.dept_name}</option>)}
          </Select>
          <p className={styles.hint}>재직 중인 현재 부서장만 지정할 수 있습니다. 제출된 평가는 작성중으로 돌아가 새 평가자가 확인 후 다시 제출합니다.</p>
        </>}
        {reasonDialog && <Textarea label="처리 사유" required={REASON_ACTIONS[reasonDialog].required} maxLength={255} value={reason} error={reasonError} onChange={(event) => setReason(event.target.value)} />}
      </div>
    </Modal>
  </div>
}
