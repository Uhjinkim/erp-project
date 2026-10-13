import { useRef, useState } from "react"
import type { ReactNode } from "react"

import { cancelPayrollConfirmation, confirmPayrollStatement } from "../../../api/payroll"
import { routeHref } from "../../../app/routing"
import { Alert, Button, Card, ConfirmDialog, EmptyState, ErrorState, Modal, Select, Spinner, Table, Textarea, TextInput } from "../../../components/ui"
import type { PayrollStatement } from "../../../types/payroll"
import { HistoryDrawer } from "../components/HistoryDrawer"
import { useManagerData } from "../hooks/useManagerData"
import { currentPeriod, departmentsOf, employeesIn, isPeriod, periodKey, periodLabel, won } from "../model"
import styles from "../payroll.module.css"

type ConfirmScreenProps = {
  enabled: boolean
  ownEmployeeNo: number | null
  search: URLSearchParams
}

type Notice = { tone: "success" | "error"; text: string; correct?: PayrollStatement }

export function ConfirmScreen({ enabled, ownEmployeeNo, search }: ConfirmScreenProps) {
  const { data, error, loading, reload } = useManagerData(enabled)
  const [period, setPeriod] = useState(() => (isPeriod(search.get("period")) ? search.get("period")! : currentPeriod()))
  const [deptKey, setDeptKey] = useState("")
  const [confirming, setConfirming] = useState<PayrollStatement | null>(null)
  const [cancelling, setCancelling] = useState<PayrollStatement | null>(null)
  const [reason, setReason] = useState("")
  const [historyFor, setHistoryFor] = useState<PayrollStatement | null>(null)
  const [notice, setNotice] = useState<Notice | null>(null)
  const [pending, setPending] = useState(false)
  const busy = useRef(false)

  if (error && !data) return <ErrorState onRetry={() => void reload()}>{error}</ErrorState>
  if (!data) return <Spinner label="확정 대상을 불러오는 중" />

  const inDepartment = deptKey ? new Set(employeesIn(data.targets, deptKey).map((employee) => employee.emp_no)) : null
  const scoped = data.statements.filter((statement) =>
    (!inDepartment || inDepartment.has(statement.employee_no)) && (!period || periodKey(statement) === period))
  const drafts = scoped.filter((statement) => statement.status === "작성중")
  const confirmed = scoped.filter((statement) => statement.status === "확정")

  async function run(action: () => Promise<unknown>, success: Notice, fallback: string) {
    if (busy.current) return
    busy.current = true
    setPending(true)
    try {
      await action()
      setNotice(success)
      setConfirming(null)
      setCancelling(null)
      setReason("")
      await reload()
    } catch (failure) {
      setNotice({ tone: "error", text: failure instanceof Error ? failure.message : fallback })
      setConfirming(null)
      setCancelling(null)
    } finally {
      busy.current = false
      setPending(false)
    }
  }

  const nameOf = (statement: PayrollStatement) => statement.employee.name ?? String(statement.employee_no)
  const selfTitle = "본인 급여는 다른 급여담당자가 처리해야 합니다."

  function statementTable(caption: string, rows: PayrollStatement[], action: (statement: PayrollStatement) => ReactNode) {
    return (
      <Table caption={caption}>
        <thead>
          <tr>
            <th scope="col">사원</th>
            <th scope="col">정산월</th>
            <th scope="col">지급일</th>
            <th scope="col">지급총액</th>
            <th scope="col">공제총액</th>
            <th scope="col">차인지급액</th>
            <th scope="col">작업</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((statement) => (
            <tr key={statement.statement_id}>
              <th scope="row">
                {nameOf(statement)}
                <span className={styles.subtext}>#{statement.employee_no}</span>
              </th>
              <td>{statement.year}.{String(statement.month).padStart(2, "0")}</td>
              <td>{statement.payment_date}</td>
              <td className={styles.amount}>{won(statement.total_earnings)}</td>
              <td className={styles.amount}>{won(statement.total_deductions)}</td>
              <td className={styles.amount}>{won(statement.net_pay)}</td>
              <td>
                <span className={styles.row}>
                  {action(statement)}
                  <Button size="small" variant="ghost" onClick={() => setHistoryFor(statement)}>이력</Button>
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    )
  }

  return (
    <div className={styles.stack}>
      <Card title="조회 조건" actions={<Button variant="secondary" size="small" pending={loading} onClick={() => void reload()}>새로고침</Button>}>
        <div className={styles.filterGrid}>
          <TextInput label="정산월" type="month" value={period} hint="비우면 전체 기간" onChange={(event) => setPeriod(event.target.value)} />
          <Select label="부서" value={deptKey} onChange={(event) => setDeptKey(event.target.value)}>
            <option value="">전체 부서</option>
            {departmentsOf(data.targets).map((department) => (
              <option key={department.key} value={department.key}>{department.name}</option>
            ))}
          </Select>
        </div>
      </Card>

      {notice && (
        <Alert tone={notice.tone}>
          <span>{notice.text}</span>
          {notice.correct && (
            <a href={routeHref({ moduleId: "payroll", screenId: "payroll-item", search: `period=${periodKey(notice.correct)}&statementId=${notice.correct.statement_id}` })}>
              사원별 정산 항목에서 정정하기
            </a>
          )}
        </Alert>
      )}

      <Card title={`확정 대기 (작성중) ${drafts.length}건`}>
        {drafts.length === 0
          ? <EmptyState title="확정 대기 중인 급여가 없습니다" />
          : statementTable(`${period ? periodLabel(period) : "전체 기간"} 확정 대기 목록`, drafts, (statement) => {
            const isSelf = statement.employee_no === ownEmployeeNo
            return <Button size="small" disabled={isSelf} title={isSelf ? selfTitle : undefined} onClick={() => setConfirming(statement)}>확정</Button>
          })}
      </Card>

      <Card title={`확정 완료 ${confirmed.length}건`}>
        {confirmed.length === 0
          ? <EmptyState title="확정된 급여가 없습니다" />
          : statementTable(`${period ? periodLabel(period) : "전체 기간"} 확정 완료 목록`, confirmed, (statement) => {
            const isSelf = statement.employee_no === ownEmployeeNo
            return <Button size="small" variant="secondary" disabled={isSelf} title={isSelf ? selfTitle : undefined} onClick={() => { setReason(""); setCancelling(statement) }}>확정취소</Button>
          })}
      </Card>

      <ConfirmDialog
        open={confirming !== null}
        title="급여 확정"
        confirmLabel="확정"
        busy={pending}
        onClose={() => setConfirming(null)}
        onConfirm={() => confirming && void run(
          () => confirmPayrollStatement(confirming.statement_id),
          { tone: "success", text: `${nameOf(confirming)} · ${confirming.year}년 ${confirming.month}월 급여를 확정했습니다.` },
          "확정하지 못했습니다.",
        )}
      >
        {confirming && (
          <p>
            {nameOf(confirming)} · {confirming.year}년 {confirming.month}월 급여(차인지급액 {won(confirming.net_pay)})를
            확정합니다. 확정 후에는 직원이 명세서를 볼 수 있고, 수정하려면 확정취소해야 합니다.
          </p>
        )}
      </ConfirmDialog>

      <Modal
        open={cancelling !== null}
        title="확정취소"
        busy={pending}
        onClose={() => setCancelling(null)}
        actions={
          <>
            <Button variant="secondary" disabled={pending} onClick={() => setCancelling(null)}>닫기</Button>
            <Button
              variant="danger"
              pending={pending}
              disabled={!reason.trim()}
              onClick={() => cancelling && void run(
                () => cancelPayrollConfirmation(cancelling.statement_id, reason.trim()),
                { tone: "success", text: `${nameOf(cancelling)} · ${cancelling.year}년 ${cancelling.month}월 급여의 확정을 취소했습니다. 작성중 상태로 돌아갔습니다.`, correct: cancelling },
                "확정취소하지 못했습니다.",
              )}
            >
              확정취소
            </Button>
          </>
        }
      >
        {cancelling && (
          <div className={styles.stack}>
            <p>
              {nameOf(cancelling)} · {cancelling.year}년 {cancelling.month}월 급여를 작성중으로 되돌립니다. 사유는 이력에
              남습니다.
            </p>
            <Textarea label="확정취소 사유" required value={reason} disabled={pending} onChange={(event) => setReason(event.target.value)} />
          </div>
        )}
      </Modal>

      <HistoryDrawer statement={historyFor} onClose={() => setHistoryFor(null)} />
    </div>
  )
}
