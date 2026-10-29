import { FormEvent, useRef, useState } from "react"

import { ApiError } from "../../../api/client"
import { createPayrollStatement } from "../../../api/payroll"
import { routeHref } from "../../../app/routing"
import { Alert, Button, Card, EmptyState, ErrorState, Spinner, TextInput } from "../../../components/ui"
import type { PayrollStatement } from "../../../types/payroll"
import { AmountFields } from "../components/AmountFields"
import { EmployeePicker } from "../components/EmployeePicker"
import { useManagerData } from "../hooks/useManagerData"
import {
  type AmountValues,
  currentPeriod,
  amountValuesFromItems,
  departmentKey,
  isPeriod,
  itemsFromAmountValues,
  missingEmployees,
  periodLabel,
  previousPeriod,
  statementFor,
} from "../model"
import styles from "../payroll.module.css"

type CreateScreenProps = {
  enabled: boolean
  ownEmployeeNo: number | null
  search: URLSearchParams
}

export function CreateScreen({ enabled, ownEmployeeNo, search }: CreateScreenProps) {
  const { data, error, reload } = useManagerData(enabled)
  const [period, setPeriod] = useState(() => (isPeriod(search.get("period")) ? search.get("period")! : currentPeriod()))
  const [deptKey, setDeptKey] = useState("")
  const [empNo, setEmpNo] = useState("")
  const [paymentDate, setPaymentDate] = useState("")
  const [amounts, setAmounts] = useState<AmountValues>({})
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({})
  const [message, setMessage] = useState("")
  const [created, setCreated] = useState<PayrollStatement | null>(null)
  // Period whose amounts were copied into the form, for the notice.
  const [copiedFrom, setCopiedFrom] = useState<string | null>(null)
  const formTop = useRef<HTMLDivElement>(null)
  const [pending, setPending] = useState(false)
  const busy = useRef(false)

  if (error && !data) return <ErrorState onRetry={() => void reload()}>{error}</ErrorState>
  if (!data) return <Spinner label="급여 대상자를 불러오는 중" />

  const statements = data.statements
  const missing = isPeriod(period) ? missingEmployees(data.targets, statements, period) : []
  const isSelf = empNo !== "" && Number(empNo) === ownEmployeeNo

  // Start from the previous month's amounts when that statement exists; otherwise a blank form.
  function prefill(nextEmp: string, nextPeriod: string) {
    const previous = nextEmp && isPeriod(nextPeriod) ? statementFor(statements, nextEmp, previousPeriod(nextPeriod)) : null
    setAmounts(previous ? amountValuesFromItems(previous.items) : {})
    setCopiedFrom(previous ? previousPeriod(nextPeriod) : null)
  }

  function choose(nextDept: string, nextEmp: string) {
    if (nextEmp && Number(nextEmp) === ownEmployeeNo) {
      setMessage("본인 급여는 다른 급여담당자가 생성해야 합니다.")
      return
    }
    setDeptKey(nextDept)
    setEmpNo(nextEmp)
    setCreated(null)
    setMessage("")
    prefill(nextEmp, period)
  }

  function chooseFromList(nextDept: string, nextEmp: string) {
    choose(nextDept, nextEmp)
    formTop.current?.scrollIntoView({ behavior: "smooth", block: "start" })
    formTop.current?.querySelector<HTMLInputElement>("input[type=number]")?.focus({ preventScroll: true })
  }

  function changePeriod(nextPeriod: string) {
    setPeriod(nextPeriod)
    prefill(empNo, nextPeriod)
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (busy.current) return
    if (isSelf) {
      setMessage("본인 급여는 다른 급여담당자가 생성해야 합니다.")
      return
    }
    if (!empNo || !isPeriod(period)) {
      setMessage("정산월과 사람을 선택해주세요.")
      return
    }
    busy.current = true
    setPending(true)
    setMessage("")
    setFieldErrors({})
    const [year, month] = period.split("-").map(Number)
    try {
      const statement = await createPayrollStatement(Number(empNo), year, month, itemsFromAmountValues(amounts), paymentDate || null)
      setCreated(statement)
      setAmounts({})
      setCopiedFrom(null)
      setPaymentDate("")
      setEmpNo("")
      await reload()
    } catch (failure) {
      setMessage(failure instanceof Error ? failure.message : "급여를 생성하지 못했습니다.")
      if (failure instanceof ApiError) setFieldErrors(failure.fieldErrors)
    } finally {
      busy.current = false
      setPending(false)
    }
  }

  const itemHref = created && routeHref({
    moduleId: "payroll",
    screenId: "payroll-item",
    search: `period=${period}&statementId=${created.statement_id}`,
  })
  const confirmHref = routeHref({ moduleId: "payroll", screenId: "payroll-confirm", search: `period=${period}` })

  return (
    <div className={styles.workspace}>
      <div ref={formTop} className={styles.scrollTarget}>
        <Card title="급여 정산 생성">
          <form className={styles.stack} onSubmit={submit} noValidate>
            {created && (
              <Alert tone="success" title="작성중으로 저장했습니다">
                <span>
                  {created.employee.name ?? created.employee_no} · {created.year}년 {created.month}월 급여가 작성중 상태로
                  생성되었습니다.
                </span>
                <span className={styles.links}>
                  <a href={itemHref!}>항목 화면에서 계속 편집</a>
                  <a href={confirmHref}>확정 화면으로 이동</a>
                </span>
              </Alert>
            )}
            {message && <Alert tone="error">{message}</Alert>}
            {copiedFrom && (
              <Alert tone="info">
                지난달({periodLabel(copiedFrom)}) 급여 금액을 불러왔습니다. 바뀐 금액만 수정한 뒤 저장하세요.
              </Alert>
            )}
            <div className={styles.fieldGrid}>
              <EmployeePicker targets={data.targets} deptKey={deptKey} empNo={empNo} onChange={choose} mode="create" disabled={pending} ownEmployeeNo={ownEmployeeNo} />
              <TextInput
                label="정산월"
                type="month"
                required
                value={period}
                disabled={pending}
                error={fieldErrors.year?.[0] ?? fieldErrors.month?.[0]}
                onChange={(event) => changePeriod(event.target.value)}
              />
              <TextInput
                label="지급일 (선택)"
                type="date"
                value={paymentDate}
                disabled={pending}
                hint="비워 두면 매월 25일(주말·공휴일이면 직전 평일)로 자동 지정됩니다. 작성중 상태에서 수정할 수 있습니다."
                error={fieldErrors.payment_date?.[0]}
                onChange={(event) => setPaymentDate(event.target.value)}
              />
            </div>
            {fieldErrors.emp_no?.[0] && <Alert tone="error">{fieldErrors.emp_no[0]}</Alert>}
            <AmountFields
              components={data.components}
              values={amounts}
              disabled={pending || isSelf || !empNo}
              onChange={(code, value) => setAmounts((previous) => ({ ...previous, [code]: value }))}
            />
            <div className={styles.formFooter}>
              <span className={styles.hint}>본인 급여는 다른 급여담당자가 처리합니다. 확정은 &lsquo;급여 확정·정정&rsquo; 화면에서 합니다.</span>
              <Button type="submit" pending={pending} disabled={isSelf || !empNo}>작성중으로 저장</Button>
            </div>
          </form>
        </Card>
      </div>

      <Card title={isPeriod(period) ? `${periodLabel(period)} 미작성 사원` : "미작성 사원"}>
        {!isPeriod(period) && <EmptyState title="정산월을 선택하세요" />}
        {isPeriod(period) && missing.length === 0 && <EmptyState title="미작성 사원이 없습니다">선택한 정산월에 급여가 없는 재직 사원이 없습니다.</EmptyState>}
        {missing.length > 0 && (
          <ul className={styles.personList}>
            {missing.map((employee) => {
              const isSelf = employee.emp_no === ownEmployeeNo
              return (
                <li key={employee.emp_no}>
                  <span>
                    <strong>{employee.name}</strong>
                    <span className={styles.hint}>{employee.dept_name ?? "부서 미지정"} · #{employee.emp_no}</span>
                  </span>
                  <Button
                    size="small"
                    variant="secondary"
                    disabled={isSelf || pending}
                    title={isSelf ? "본인 급여는 다른 급여담당자가 생성해야 합니다." : undefined}
                    onClick={() => chooseFromList(departmentKey(employee), String(employee.emp_no))}
                  >
                    {isSelf ? "본인(생성 불가)" : "선택"}
                  </Button>
                </li>
              )
            })}
          </ul>
        )}
      </Card>
    </div>
  )
}
