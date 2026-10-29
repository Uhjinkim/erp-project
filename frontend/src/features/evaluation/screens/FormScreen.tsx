import { ArrowLeft } from "lucide-react"
import { FormEvent, useCallback, useEffect, useRef, useState } from "react"

import { Alert, Badge, Button, Card, ConfirmDialog, DetailList, EmptyState, ErrorState, Select, Spinner, Textarea, TextInput } from "../../../components/ui"
import { ApiError } from "../../../api/client"
import {
  createEvaluation,
  getEvaluation,
  getEvaluationHistory,
  listEvaluationTargets,
  reviseEvaluation,
  submitEvaluation,
} from "../../../api/evaluation"
import type { CurrentUser } from "../../../types/auth"
import type { Evaluation, EvaluationHistoryEntry, EvaluationTargetOption } from "../../../types/evaluation"
import { EvaluationHistory } from "../components/EvaluationHistory"
import { EDITABLE, STATUS_TONE, creatableYears, errorText, evaluationHref, formatDateTime, go } from "../model"
import styles from "../evaluation.module.css"

type Props = { user: CurrentUser; enabled: boolean; search?: string }
type FieldErrors = Record<string, string[]>

/** evaluation-form: create (?empNo=&year=) or open an evaluation (?evalId=) to revise and submit. */
export function FormScreen({ user, enabled, search }: Props) {
  const params = new URLSearchParams(search ?? "")
  const evalId = Number(params.get("evalId")) || null
  return evalId
    ? <EvaluationEditor key={evalId} evalId={evalId} user={user} enabled={enabled} />
    : <CreateForm key={search ?? ""} enabled={enabled} empNo={params.get("empNo") ?? ""} year={params.get("year") ?? ""} />
}

function firstError(errors: FieldErrors, key: string) {
  return errors[key]?.[0]
}

function CreateForm({ enabled, empNo, year }: { enabled: boolean; empNo: string; year: string }) {
  const years = creatableYears()
  const [form, setForm] = useState({ emp_no: empNo, eval_year: years.includes(year) ? year : years[0], score: "", comments: "" })
  const [targets, setTargets] = useState<EvaluationTargetOption[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState("")
  const [errors, setErrors] = useState<FieldErrors>({})
  const generation = useRef(0)

  useEffect(() => {
    if (!enabled) return
    const run = ++generation.current
    const timer = window.setTimeout(() => {
      setLoading(true)
      listEvaluationTargets(form.eval_year)
        .then((items) => { if (run === generation.current) setTargets(items) })
        .catch((caught) => { if (run === generation.current) setMessage(errorText(caught, "평가 대상을 불러오지 못했습니다.")) })
        .finally(() => { if (run === generation.current) setLoading(false) })
    }, 0)
    return () => window.clearTimeout(timer)
  }, [enabled, form.eval_year])

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (saving) return
    setSaving(true)
    setMessage("")
    setErrors({})
    try {
      const created = await createEvaluation({ ...form, emp_no: Number(form.emp_no) })
      go("evaluation-form", { evalId: String(created.eval_id) })
    } catch (caught) {
      if (caught instanceof ApiError) setErrors(caught.fieldErrors)
      setMessage(errorText(caught, "평가를 저장하지 못했습니다."))
      setSaving(false)
    }
  }

  return <div className={styles.stack}>
    <a className={styles.link} href={evaluationHref("evaluation-team")}><ArrowLeft size={16} aria-hidden="true" />팀 평가 대상 목록</a>
    <Card title="평가 작성">
      <form className={styles.form} onSubmit={submit}>
        {message && <Alert tone="error">{message}</Alert>}
        <Select label="평가 연도" value={form.eval_year} error={firstError(errors, "eval_year")} onChange={(event) => setForm({ ...form, eval_year: event.target.value, emp_no: "" })}>
          {years.map((item) => <option key={item} value={item}>{item}</option>)}
        </Select>
        {loading ? <Spinner label="평가 대상을 불러오는 중" /> : targets.length === 0
          ? <EmptyState title="이 연도에 새로 평가할 대상이 없습니다">이미 평가가 있거나 근무 3개월 이하인 사원은 목록에 나오지 않습니다.</EmptyState>
          : <Select label="평가 대상" required value={form.emp_no} error={firstError(errors, "emp_no")} onChange={(event) => setForm({ ...form, emp_no: event.target.value })}>
            <option value="">선택하세요</option>
            {targets.map((target) => <option key={target.emp_no} value={target.emp_no}>{target.name ?? "이름 없음"} ({target.emp_no})</option>)}
          </Select>}
        <TextInput label="점수 (0~100)" required type="number" min="0" max="100" step="0.01" value={form.score} error={firstError(errors, "score")} onChange={(event) => setForm({ ...form, score: event.target.value })} hint="등급은 자동 계산됩니다. S 90점 이상, A 80점 이상, B 70점 이상, C 70점 미만." />
        <Textarea label="평가 의견" value={form.comments} error={firstError(errors, "comments")} onChange={(event) => setForm({ ...form, comments: event.target.value })} />
        <div className={styles.actions}>
          <Button type="submit" pending={saving} disabled={!enabled || targets.length === 0}>작성중으로 저장</Button>
        </div>
      </form>
    </Card>
  </div>
}

function EvaluationEditor({ evalId, user, enabled }: { evalId: number; user: CurrentUser; enabled: boolean }) {
  const myNo = user.employee?.emp_no ?? 0
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null)
  const [history, setHistory] = useState<EvaluationHistoryEntry[]>([])
  const [form, setForm] = useState({ score: "", comments: "" })
  const [loadError, setLoadError] = useState("")
  const [message, setMessage] = useState<{ tone: "success" | "error"; text: string } | null>(null)
  const [errors, setErrors] = useState<FieldErrors>({})
  const [busy, setBusy] = useState<"" | "save" | "submit">("")
  const [confirmSubmit, setConfirmSubmit] = useState(false)

  // A failed save keeps the typed values so the user can correct them instead of retyping.
  const load = useCallback(async (resetForm = true) => {
    if (!enabled) return
    setLoadError("")
    try {
      const detail = await getEvaluation(evalId)
      setEvaluation(detail)
      if (resetForm) setForm({ score: detail.score, comments: detail.comments })
      // History is only for the current evaluator and HR; others simply see none.
      setHistory(await getEvaluationHistory(evalId).catch(() => []))
    } catch (caught) {
      setLoadError(errorText(caught, "평가를 불러오지 못했습니다."))
    }
  }, [enabled, evalId])

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0)
    return () => window.clearTimeout(timer)
  }, [load])

  async function run(kind: "save" | "submit", action: () => Promise<Evaluation>, done: string) {
    if (busy) return
    setBusy(kind)
    setMessage(null)
    setErrors({})
    try {
      await action()
      await load()
      setMessage({ tone: "success", text: done })
    } catch (caught) {
      if (caught instanceof ApiError) setErrors(caught.fieldErrors)
      setMessage({ tone: "error", text: errorText(caught, "처리하지 못했습니다.") })
      await load(false)
    } finally {
      setBusy("")
      setConfirmSubmit(false)
    }
  }

  if (loadError) return <ErrorState onRetry={() => void load()}>{loadError}</ErrorState>
  if (!evaluation) return <Spinner label="평가를 불러오는 중" />

  const canEdit = evaluation.evaluator_no === myNo && EDITABLE.includes(evaluation.eval_status)
  return <div className={styles.stack}>
    <a className={styles.link} href={evaluationHref("evaluation-team")}><ArrowLeft size={16} aria-hidden="true" />팀 평가 대상 목록</a>
    <div className={styles.workspace}>
      <Card title={`${evaluation.employee_name ?? evaluation.emp_no} · ${evaluation.eval_year}`} actions={<Badge tone={STATUS_TONE[evaluation.eval_status]}>{evaluation.eval_status}</Badge>}>
        <div className={styles.form}>
          {message && <Alert tone={message.tone}>{message.text}</Alert>}
          <DetailList items={[
            { key: "score", label: "점수", value: evaluation.score },
            { key: "grade", label: "등급", value: evaluation.grade },
            { key: "evaluator", label: "현재 평가자", value: evaluation.evaluator_name ?? evaluation.evaluator_no },
            { key: "dept", label: "기준 부서", value: evaluation.snapshot_dept_no ?? "-" },
            { key: "confirmed", label: "확정", value: evaluation.confirmed_by ? `${evaluation.confirmed_by} · ${formatDateTime(evaluation.confirmed_at)}` : "-" },
          ]} />
          {canEdit ? <form className={styles.form} onSubmit={(event) => { event.preventDefault(); void run("save", () => reviseEvaluation(evalId, form), "저장했습니다.") }}>
            <TextInput label="점수 (0~100)" required type="number" min="0" max="100" step="0.01" value={form.score} error={firstError(errors, "score")} onChange={(event) => setForm({ ...form, score: event.target.value })} />
            <Textarea label="평가 의견" value={form.comments} error={firstError(errors, "comments")} onChange={(event) => setForm({ ...form, comments: event.target.value })} />
            <div className={styles.actions}>
              <Button type="submit" variant="secondary" pending={busy === "save"} disabled={!!busy}>저장</Button>
              <Button pending={busy === "submit"} disabled={!!busy} onClick={() => setConfirmSubmit(true)}>제출</Button>
            </div>
            {evaluation.eval_status === "반려" && <p className={styles.hint}>반려된 평가입니다. 처리 이력의 사유를 확인하고 수정한 뒤 다시 제출하세요.</p>}
          </form> : <>
            {evaluation.comments && <p className={styles.comments}>{evaluation.comments}</p>}
            {evaluation.evaluator_no === myNo && <p className={styles.hint}>{evaluation.eval_status} 상태에서는 수정할 수 없습니다.</p>}
          </>}
        </div>
      </Card>
      <EvaluationHistory entries={history} />
    </div>
    <ConfirmDialog open={confirmSubmit} title="평가를 제출할까요?" confirmLabel="제출" busy={busy === "submit"} onClose={() => setConfirmSubmit(false)}
      onConfirm={() => void run("submit", async () => {
        if (form.score !== evaluation.score || form.comments !== evaluation.comments) await reviseEvaluation(evalId, form)
        return submitEvaluation(evalId)
      }, "평가를 제출했습니다.")}>
      <p>저장하지 않은 수정 내용도 함께 저장한 뒤 제출합니다. 제출하면 인사관리자가 반려하기 전까지 수정할 수 없습니다.</p>
    </ConfirmDialog>
  </div>
}
