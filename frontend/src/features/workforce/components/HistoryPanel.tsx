import { useCallback, useState } from "react"
import type { FormEvent } from "react"
import { cancelHistory, correctHistory, getEmploymentHistory, getHistoryChanges, transferEmployee } from "../../../api/workforce"
import { Alert, Badge, Button, Card, ConfirmDialog, EmptyState, Modal, Select, Table, TextInput, Textarea } from "../../../components/ui"
import type { EmployeeDetail, HistoryChange, HistoryEntry, HistoryValues, TransferResult } from "../../../types/workforce"
import type { MasterData } from "../hooks"
import { useMutation, useWorkforceQuery } from "../hooks"
import { departmentLabel, firstFieldErrors, formatAmount, formatDateTime, isSalary, latestHistory, localToday, positionLabel, sortHistoryDesc } from "../model"
import styles from "../workforce.module.css"
import { QueryFallback } from "./QueryFallback"

type HistoryPanelProps = {
  employee: EmployeeDetail
  master: MasterData
  enabled: boolean
  onChanged: () => void
}

type Values = { start_date: string; dept_no: string; position_code: string; base_salary: string }

// FN-HR-010 인사이력 조회·발령 등록·최근 이력 정정·취소. 기간 중복과 대상 판정은 서버가 담당한다(HR-010).
export function HistoryPanel({ employee, master, enabled, onChanged }: HistoryPanelProps) {
  const loadHistory = useCallback(() => getEmploymentHistory(employee.emp_no), [employee.emp_no])
  const loadChanges = useCallback(() => getHistoryChanges(employee.emp_no), [employee.emp_no])
  const history = useWorkforceQuery(enabled, loadHistory)
  const changes = useWorkforceQuery(enabled, loadChanges)
  const [result, setResult] = useState<{ message: string; detail: TransferResult } | null>(null)
  const [correcting, setCorrecting] = useState<HistoryEntry | null>(null)
  const [cancelling, setCancelling] = useState<HistoryEntry | null>(null)

  const entries = history.data ? sortHistoryDesc(history.data) : []
  const latest = history.data ? latestHistory(history.data) : null
  const retired = employee.tenure_status === "퇴사"

  function completed(message: string, detail: TransferResult) {
    setResult({ message, detail })
    setCorrecting(null)
    setCancelling(null)
    void history.reload()
    void changes.reload()
    onChanged()
  }

  return (
    <div className={styles.stack}>
      {result && <ResultNotice message={result.message} result={result.detail} master={master} />}
      <Card title="인사이력" actions={<Button variant="secondary" size="small" pending={history.loading} onClick={() => void history.reload()}>새로고침</Button>}>
        <QueryFallback query={history} label="인사이력을 불러오는 중" />
        {history.data && history.error && <p className={styles.hint} role="alert">{history.error}</p>}
        {history.data && entries.length === 0 && <EmptyState title="등록된 인사이력이 없습니다">첫 발령을 등록하면 입사일부터의 이전 기간 이력도 함께 기록합니다.</EmptyState>}
        {entries.length > 0 && (
          <Table caption="기간별 인사이력">
            <thead><tr><th scope="col">기간</th><th scope="col">부서</th><th scope="col">직급</th><th scope="col" className={styles.amount}>기본급</th><th scope="col">작업</th></tr></thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.history_id}>
                  <th scope="row" className={styles.nowrap}>{entry.start_date} ~ {entry.end_date ?? "진행 중"}</th>
                  <td>{entry.dept_name ?? departmentLabel(master.departments, entry.dept_no)}</td>
                  <td>{entry.position_name ?? positionLabel(master.positions, entry.position_code)}</td>
                  <td className={styles.amount}>{formatAmount(entry.base_salary)}</td>
                  <td>
                    {entry === latest && entry.end_date === null
                      ? <span className={styles.row}>
                          <Button size="small" variant="secondary" onClick={() => setCorrecting(entry)}>정정</Button>
                          <Button size="small" variant="ghost" onClick={() => setCancelling(entry)}>취소</Button>
                        </span>
                      : <span className={styles.subtext}>-</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      {retired
        ? <Alert tone="info">퇴사한 사원은 발령을 등록할 수 없습니다. 재입사는 새 사번으로 처리합니다.</Alert>
        : history.data && <TransferForm employee={employee} master={master} needsPreviousSalary={history.data.length === 0} onDone={(detail) => completed("발령을 등록했습니다.", detail)} />}

      <Card title="변경 기록">
        <QueryFallback query={changes} label="변경 기록을 불러오는 중" />
        {changes.data && changes.data.length === 0 && <p className={styles.hint}>발령·정정·취소 기록이 없습니다.</p>}
        {changes.data && changes.data.length > 0 && <ChangeTimeline changes={changes.data} master={master} />}
      </Card>

      {correcting && (
        <CorrectionDialog key={correcting.history_id} employee={employee} entry={correcting} master={master} onClose={() => setCorrecting(null)} onDone={(detail) => completed("최근 이력을 정정했습니다.", detail)} />
      )}
      {cancelling && (
        <CancellationDialog employee={employee} entry={cancelling} onClose={() => setCancelling(null)} onDone={(detail) => completed("최근 발령을 취소했습니다.", detail)} />
      )}
    </div>
  )
}

function ResultNotice({ message, result, master }: { message: string; result: TransferResult; master: MasterData }) {
  const names = (numbers: number[]) => numbers.map((no) => departmentLabel(master.departments, no)).join(", ")
  return (
    <Alert tone="success" title={message}>
      {result.released_head_dept_nos.length > 0 && <p>부서장 지정이 해제된 부서: {names(result.released_head_dept_nos)}</p>}
      {result.restored_head_dept_nos.length > 0 && <p>부서장 지정이 복원된 부서: {names(result.restored_head_dept_nos)}</p>}
    </Alert>
  )
}

function TransferForm({ employee, master, needsPreviousSalary, onDone }: {
  employee: EmployeeDetail; master: MasterData; needsPreviousSalary: boolean; onDone: (result: TransferResult) => void
}) {
  const initial = { start_date: localToday(), dept_no: String(employee.dept_no ?? ""), position_code: employee.position_code ?? "", base_salary: "", previous_base_salary: "", reason: "" }
  const [form, setForm] = useState(initial)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const mutation = useMutation()
  const showPrevious = needsPreviousSalary && form.start_date > employee.hire_date

  async function submit(event: FormEvent) {
    event.preventDefault()
    const local: Record<string, string> = {}
    if (!form.start_date) local.start_date = "발령일을 입력하세요."
    if (!form.dept_no) local.dept_no = "부서를 선택하세요."
    if (!form.position_code) local.position_code = "직급을 선택하세요."
    if (!isSalary(form.base_salary)) local.base_salary = "기본급은 0 이상의 숫자로 입력하세요."
    if (showPrevious && !isSalary(form.previous_base_salary)) local.previous_base_salary = "이전 기간 기본급을 입력하세요."
    setErrors(local)
    if (Object.keys(local).length) return
    const result = await mutation.run(() => transferEmployee(employee.emp_no, {
      start_date: form.start_date,
      dept_no: Number(form.dept_no),
      position_code: form.position_code,
      base_salary: form.base_salary.trim(),
      previous_base_salary: showPrevious ? form.previous_base_salary.trim() : null,
      reason: form.reason.trim() || null,
    }))
    if (result) {
      setForm(initial)
      onDone(result)
    }
  }

  const fieldError = (key: string) => errors[key] ?? firstFieldErrors(mutation.fieldErrors)[key]
  return (
    <Card title="발령 등록">
      <form className={styles.stack} onSubmit={(event) => void submit(event)} noValidate>
        <p className={styles.hint}>부서 또는 직급이 바뀌는 발령만 등록할 수 있습니다. 진행 중 이력은 발령일 전날로 마감됩니다.</p>
        {mutation.error && <Alert tone="error">{mutation.error}</Alert>}
        <fieldset className={styles.fieldset} disabled={mutation.pending}>
          <legend>발령 내용</legend>
          <div className={styles.fieldGrid}>
            <TextInput label="발령일" type="date" required min={employee.hire_date} max={localToday()} value={form.start_date} error={fieldError("start_date")} onChange={(event) => setForm({ ...form, start_date: event.target.value })} />
            <TextInput label="기본급(원)" required inputMode="decimal" value={form.base_salary} error={fieldError("base_salary")} onChange={(event) => setForm({ ...form, base_salary: event.target.value })} />
            <Select label="부서" required value={form.dept_no} error={fieldError("dept_no")} onChange={(event) => setForm({ ...form, dept_no: event.target.value })}>
              <option value="">선택</option>
              {master.departments.map((item) => <option key={item.dept_no} value={item.dept_no}>{item.dept_name}</option>)}
            </Select>
            <Select label="직급" required value={form.position_code} error={fieldError("position_code")} onChange={(event) => setForm({ ...form, position_code: event.target.value })}>
              <option value="">선택</option>
              {master.positions.map((item) => <option key={item.position_code} value={item.position_code}>{item.position_name}</option>)}
            </Select>
            {showPrevious && (
              <TextInput label="이전 기간 기본급(원)" required inputMode="decimal" value={form.previous_base_salary} error={fieldError("previous_base_salary")} hint={`입사일(${employee.hire_date})부터 발령 전날까지의 기간 이력에 기록됩니다.`} onChange={(event) => setForm({ ...form, previous_base_salary: event.target.value })} />
            )}
            <div className={styles.fullWidth}>
              <Textarea label="발령 사유" maxLength={500} rows={2} value={form.reason} error={fieldError("reason")} onChange={(event) => setForm({ ...form, reason: event.target.value })} />
            </div>
          </div>
        </fieldset>
        <div className={styles.formFooter}><Button type="submit" pending={mutation.pending}>발령 등록</Button></div>
      </form>
    </Card>
  )
}

function CorrectionDialog({ employee, entry, master, onClose, onDone }: {
  employee: EmployeeDetail; entry: HistoryEntry; master: MasterData; onClose: () => void; onDone: (result: TransferResult) => void
}) {
  const [form, setForm] = useState<Values & { reason: string }>({
    start_date: entry.start_date, dept_no: String(entry.dept_no), position_code: entry.position_code, base_salary: String(entry.base_salary), reason: "",
  })
  const [localError, setLocalError] = useState("")
  const mutation = useMutation()
  const errors = firstFieldErrors(mutation.fieldErrors)

  async function submit() {
    if (!form.reason.trim()) return setLocalError("정정 사유를 입력하세요.")
    if (!isSalary(form.base_salary)) return setLocalError("기본급은 0 이상의 숫자로 입력하세요.")
    setLocalError("")
    const result = await mutation.run(() => correctHistory(employee.emp_no, entry.history_id, {
      start_date: form.start_date, dept_no: Number(form.dept_no), position_code: form.position_code,
      base_salary: form.base_salary.trim(), reason: form.reason.trim(),
    }))
    if (result) onDone(result)
  }

  return (
    <Modal open title="최근 이력 정정" onClose={onClose} busy={mutation.pending} actions={<>
      <Button variant="secondary" onClick={onClose} disabled={mutation.pending}>닫기</Button>
      <Button pending={mutation.pending} onClick={() => void submit()}>정정 저장</Button>
    </>}>
      <div className={styles.stack}>
        <p className={styles.hint}>정정 전·후 값과 사유가 변경 기록에 남습니다.</p>
        {(localError || mutation.error) && <Alert tone="error">{localError || mutation.error}</Alert>}
        <TextInput label="시작일" type="date" required max={localToday()} value={form.start_date} error={errors.start_date} onChange={(event) => setForm({ ...form, start_date: event.target.value })} />
        <Select label="부서" required value={form.dept_no} error={errors.dept_no} onChange={(event) => setForm({ ...form, dept_no: event.target.value })}>
          {master.departments.map((item) => <option key={item.dept_no} value={item.dept_no}>{item.dept_name}</option>)}
        </Select>
        <Select label="직급" required value={form.position_code} error={errors.position_code} onChange={(event) => setForm({ ...form, position_code: event.target.value })}>
          {master.positions.map((item) => <option key={item.position_code} value={item.position_code}>{item.position_name}</option>)}
        </Select>
        <TextInput label="기본급(원)" required inputMode="decimal" value={form.base_salary} error={errors.base_salary} onChange={(event) => setForm({ ...form, base_salary: event.target.value })} />
        <Textarea label="정정 사유" required maxLength={500} rows={3} value={form.reason} error={errors.reason} onChange={(event) => setForm({ ...form, reason: event.target.value })} />
      </div>
    </Modal>
  )
}

function CancellationDialog({ employee, entry, onClose, onDone }: {
  employee: EmployeeDetail; entry: HistoryEntry; onClose: () => void; onDone: (result: TransferResult) => void
}) {
  const [reason, setReason] = useState("")
  const [localError, setLocalError] = useState("")
  const mutation = useMutation()

  async function confirm() {
    if (!reason.trim()) return setLocalError("취소 사유를 입력하세요.")
    setLocalError("")
    const result = await mutation.run(() => cancelHistory(employee.emp_no, entry.history_id, reason.trim()))
    if (result) onDone(result)
  }

  return (
    <ConfirmDialog open danger title="최근 발령 취소" confirmLabel="발령 취소" busy={mutation.pending} onClose={onClose} onConfirm={() => void confirm()}>
      <div className={styles.stack}>
        <p>{entry.start_date}부터 진행 중인 이력을 취소하고 직전 이력을 다시 진행 중으로 되돌립니다.</p>
        {(localError || mutation.error) && <Alert tone="error">{localError || mutation.error}</Alert>}
        <Textarea label="취소 사유" required maxLength={500} rows={3} value={reason} error={firstFieldErrors(mutation.fieldErrors).reason} onChange={(event) => setReason(event.target.value)} />
      </div>
    </ConfirmDialog>
  )
}

const valueFields: { key: keyof HistoryValues; label: string }[] = [
  { key: "start_date", label: "시작일" }, { key: "end_date", label: "종료일" }, { key: "dept_no", label: "부서" },
  { key: "position_code", label: "직급" }, { key: "base_salary", label: "기본급" },
]

function ChangeTimeline({ changes, master }: { changes: HistoryChange[]; master: MasterData }) {
  const display = (key: keyof HistoryValues, values: HistoryValues | null) => {
    if (!values) return "-"
    if (key === "dept_no") return departmentLabel(master.departments, values.dept_no)
    if (key === "position_code") return positionLabel(master.positions, values.position_code)
    if (key === "base_salary") return formatAmount(values.base_salary)
    return values[key] ?? "진행 중"
  }
  const sorted = [...changes].sort((a, b) => b.changed_at.localeCompare(a.changed_at))
  return (
    <ol className={styles.timeline}>
      {sorted.map((change, index) => (
        <li key={`${change.history_id}-${change.changed_at}-${index}`}>
          <span className={styles.row}>
            <Badge tone={change.action === "취소" ? "warning" : change.action === "정정" ? "info" : "neutral"}>{change.action}</Badge>
            <span className={styles.subtext}>{formatDateTime(change.changed_at)} · 처리자 {change.changed_by ?? "시스템"}</span>
          </span>
          {change.reason && <p>사유: {change.reason}</p>}
          <dl className={styles.compare}>
            <dt>항목</dt><dd>변경 전</dd><dd>변경 후</dd>
            {valueFields.map(({ key, label }) => {
              const before = display(key, change.before)
              const after = display(key, change.after)
              const changed = before !== after
              return [
                <dt key={`${key}-label`}>{label}</dt>,
                <dd key={`${key}-before`}>{before}</dd>,
                <dd key={`${key}-after`} className={changed ? styles.changed : undefined}>{after}{changed && <span className={styles.subtext}> (변경)</span>}</dd>,
              ]
            })}
          </dl>
        </li>
      ))}
    </ol>
  )
}
