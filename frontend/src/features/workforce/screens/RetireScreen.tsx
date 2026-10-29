import { useCallback, useState } from "react"
import type { FormEvent } from "react"
import { getEmployeeDetail, listEmployees, terminateEmployee } from "../../../api/workforce"
import { Alert, Button, Card, ConfirmDialog, EmptyState, TextInput } from "../../../components/ui"
import type { EmployeeDetail } from "../../../types/workforce"
import { EmployeeLookup } from "../components/EmployeeLookup"
import type { LookupRow } from "../components/EmployeeLookup"
import { EmployeeSummary } from "../components/EmployeeSummary"
import { QueryFallback } from "../components/QueryFallback"
import type { MasterData } from "../hooks"
import { useMutation, useWorkforceQuery } from "../hooks"
import { departmentLabel, firstFieldErrors, localToday, parseId, positionLabel, workforceHref } from "../model"
import styles from "../workforce.module.css"

// Query key: empNo. 없으면 재직·휴직 사원 검색으로 대상을 고른다.
export function RetireScreen({ enabled, search, master }: { enabled: boolean; search: URLSearchParams; master: MasterData }) {
  const empNo = parseId(search.get("empNo"))
  const loadActive = useCallback(async (keyword: string): Promise<LookupRow[]> => {
    const rows = await listEmployees({ search: keyword })
    return rows.filter((row) => row.tenure_status !== "퇴사").map((row) => ({
      emp_no: row.emp_no, name: row.name, status: row.tenure_status,
      organization: `${departmentLabel(master.departments, row.dept_no)} · ${positionLabel(master.positions, row.position_code)}`,
      dates: `${row.hire_date} 입사`,
    }))
  }, [master])
  if (empNo === null) {
    return <EmployeeLookup title="퇴사 처리 대상 선택" description="재직 또는 휴직 중인 사원을 검색합니다." enabled={enabled} load={loadActive} hrefFor={(row) => workforceHref("retire", { empNo: row.emp_no })} actionLabel="퇴사 처리" />
  }
  return <RetireView empNo={empNo} enabled={enabled} />
}

function RetireView({ empNo, enabled }: { empNo: number; enabled: boolean }) {
  const load = useCallback(() => getEmployeeDetail(empNo), [empNo])
  const detail = useWorkforceQuery(enabled, load)
  const [done, setDone] = useState<EmployeeDetail | null>(null)
  if (done) {
    return (
      <Card title="퇴사 처리를 완료했습니다">
        <Alert tone="success">{done.name}(사번 {done.emp_no})의 퇴사일이 {done.term_date}로 기록되었습니다. 인사이력·평가·급여 기록은 보존됩니다.</Alert>
        <EmployeeSummary employee={done} />
        <div className={styles.formFooter}><a href={workforceHref("employee-detail", { empNo: done.emp_no })}>사원 상세 보기</a></div>
      </Card>
    )
  }
  if (!detail.data) return <QueryFallback query={detail} label="사원 정보를 불러오는 중" />
  if (detail.data.tenure_status === "퇴사") {
    return <EmptyState title="이미 퇴사 처리된 사원입니다" action={<a href={workforceHref("rehire", { empNo })}>재입사 처리로 이동</a>}>퇴사일: {detail.data.term_date ?? "-"}</EmptyState>
  }
  return <RetireForm employee={detail.data} onDone={setDone} />
}

function RetireForm({ employee, onDone }: { employee: EmployeeDetail; onDone: (employee: EmployeeDetail) => void }) {
  const [termDate, setTermDate] = useState(localToday())
  const [localError, setLocalError] = useState("")
  const [confirming, setConfirming] = useState(false)
  const mutation = useMutation()

  function review(event: FormEvent) {
    event.preventDefault()
    if (!termDate) return setLocalError("퇴사일을 입력하세요.")
    if (termDate < employee.hire_date) return setLocalError("퇴사일은 입사일보다 빠를 수 없습니다.")
    setLocalError("")
    mutation.reset()
    setConfirming(true)
  }

  async function confirm() {
    const result = await mutation.run(() => terminateEmployee(employee.emp_no, termDate))
    setConfirming(false)
    if (result) onDone(result)
  }

  return (
    <div className={styles.stack}>
      <Card title="퇴사 처리 대상" actions={<a href={workforceHref("employee-detail", { empNo: employee.emp_no })}>사원 상세</a>}>
        <EmployeeSummary employee={employee} />
      </Card>
      <Card title="퇴사 처리">
        <form className={styles.stack} onSubmit={review} noValidate>
          <Alert tone="warning" title="처리 후 되돌릴 수 없습니다">
            퇴사 처리 후 해당 사원은 로그인과 ERP 기능을 이용할 수 없고 새 휴가를 신청할 수 없습니다.
            인사이력·역할·평가·급여 기록은 삭제하지 않고 보존합니다.
          </Alert>
          {mutation.error && <Alert tone="error" title="퇴사 처리를 완료하지 못했습니다">{mutation.error}</Alert>}
          <TextInput label="퇴사일" type="date" required min={employee.hire_date} max={localToday()} value={termDate} error={localError || firstFieldErrors(mutation.fieldErrors).term_date} hint="입사일 이후, 오늘 또는 이전 날짜만 지정할 수 있습니다." onChange={(event) => setTermDate(event.target.value)} />
          <div className={styles.formFooter}>
            <a href={workforceHref("employee-detail", { empNo: employee.emp_no })}>취소</a>
            <Button type="submit" variant="danger">퇴사 처리 확인</Button>
          </div>
        </form>
      </Card>
      <ConfirmDialog open={confirming} danger title="퇴사 처리" confirmLabel="퇴사 처리" busy={mutation.pending} onClose={() => setConfirming(false)} onConfirm={() => void confirm()}>
        <p>{employee.name}(사번 {employee.emp_no})을 {termDate} 자로 퇴사 처리합니다.</p>
      </ConfirmDialog>
    </div>
  )
}
