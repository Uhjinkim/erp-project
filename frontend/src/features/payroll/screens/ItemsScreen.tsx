import { useRef, useState } from "react"

import { downloadPayslipExcel, updatePayrollItems } from "../../../api/payroll"
import { routeHref } from "../../../app/routing"
import { Alert, Badge, Button, Card, EmptyState, ErrorState, Select, Spinner, Table, TextInput } from "../../../components/ui"
import type { PayrollStatement, PayrollStatus } from "../../../types/payroll"
import { AmountFields } from "../components/AmountFields"
import { EmployeePicker } from "../components/EmployeePicker"
import { HistoryDrawer } from "../components/HistoryDrawer"
import { PayslipView } from "../components/PayslipView"
import { useManagerData } from "../hooks/useManagerData"
import { usePayslipPrint } from "../hooks/usePayslipPrint"
import {
  type AmountValues,
  amountValuesFromItems,
  currentPeriod,
  employeesIn,
  isPeriod,
  itemsFromAmountValues,
  periodKey,
  statusTone,
  won,
} from "../model"
import styles from "../payroll.module.css"

type ItemsScreenProps = {
  enabled: boolean
  ownEmployeeNo: number | null
  search: URLSearchParams
}

type Editor = { statementId: number; paymentDate: string; amounts: AmountValues }
type Notice = { tone: "success" | "error"; text: string }

export function ItemsScreen({ enabled, ownEmployeeNo, search }: ItemsScreenProps) {
  const { data, error, loading, reload } = useManagerData(enabled)
  const [deptKey, setDeptKey] = useState("")
  const [empNo, setEmpNo] = useState("")
  const [period, setPeriod] = useState(() => (isPeriod(search.get("period")) ? search.get("period")! : currentPeriod()))
  const [status, setStatus] = useState<"" | PayrollStatus>("")
  const [selectedId, setSelectedId] = useState<number | null>(() => Number(search.get("statementId")) || null)
  const [editor, setEditor] = useState<Editor | null>(null)
  const [historyFor, setHistoryFor] = useState<PayrollStatement | null>(null)
  const [notice, setNotice] = useState<Notice | null>(null)
  const [pending, setPending] = useState(false)
  const busy = useRef(false)
  const { printingId, print } = usePayslipPrint()

  if (error && !data) return <ErrorState onRetry={() => void reload()}>{error}</ErrorState>
  if (!data) return <Spinner label="정산 항목을 불러오는 중" />

  const targetByEmployee = new Map(data.targets.map((employee) => [employee.emp_no, employee]))
  const inDepartment = deptKey ? new Set(employeesIn(data.targets, deptKey).map((employee) => employee.emp_no)) : null
  const visible = data.statements.filter((statement) =>
    (!inDepartment || inDepartment.has(statement.employee_no))
    && (!empNo || String(statement.employee_no) === empNo)
    && (!period || periodKey(statement) === period)
    && (!status || statement.status === status))
  const selected = data.statements.find((statement) => statement.statement_id === selectedId) ?? null
  const isOwn = selected?.employee_no === ownEmployeeNo

  function select(statement: PayrollStatement) {
    setSelectedId(statement.statement_id)
    setEditor(null)
    setNotice(null)
  }

  async function save() {
    if (!editor || busy.current) return
    const items = itemsFromAmountValues(editor.amounts)
    if (items.length === 0) {
      setNotice({ tone: "error", text: "구성항목을 최소 1건 이상 입력해야 합니다." })
      return
    }
    busy.current = true
    setPending(true)
    try {
      await updatePayrollItems(editor.statementId, items, editor.paymentDate || null)
      setEditor(null)
      setNotice({ tone: "success", text: "급여 내용을 저장했습니다." })
      await reload()
    } catch (failure) {
      setNotice({ tone: "error", text: failure instanceof Error ? failure.message : "구성항목을 저장하지 못했습니다." })
    } finally {
      busy.current = false
      setPending(false)
    }
  }

  async function saveExcel(statement: PayrollStatement) {
    try {
      await downloadPayslipExcel(statement)
    } catch (failure) {
      setNotice({ tone: "error", text: failure instanceof Error ? failure.message : "급여명세서를 내려받지 못했습니다." })
    }
  }

  return (
    <div className={styles.stack}>
      <Card title="조회 조건" actions={<Button variant="secondary" size="small" pending={loading} onClick={() => void reload()}>새로고침</Button>}>
        <div className={styles.filterGrid}>
          <EmployeePicker
            targets={data.targets}
            deptKey={deptKey}
            empNo={empNo}
            mode="filter"
            onChange={(nextDept, nextEmp) => { setDeptKey(nextDept); setEmpNo(nextEmp) }}
          />
          <TextInput label="정산월" type="month" value={period} hint="비우면 전체 기간" onChange={(event) => setPeriod(event.target.value)} />
          <Select label="상태" value={status} onChange={(event) => setStatus(event.target.value as "" | PayrollStatus)}>
            <option value="">전체</option>
            <option value="작성중">작성중</option>
            <option value="확정">확정</option>
          </Select>
        </div>
      </Card>

      <div className={styles.workspace}>
        <Card title={`정산 목록 ${visible.length}건`}>
          {visible.length === 0 ? (
            <EmptyState title="조건에 맞는 급여가 없습니다">
              미작성 사원은 <a href={routeHref({ moduleId: "payroll", screenId: "payroll-create", search: period ? `period=${period}` : undefined })}>급여 정산 생성</a>에서 만들 수 있습니다.
            </EmptyState>
          ) : (
            <Table caption="사원별 정산 목록">
              <thead>
                <tr>
                  <th scope="col">사원</th>
                  <th scope="col">정산월</th>
                  <th scope="col">차인지급액</th>
                  <th scope="col">상태</th>
                  <th scope="col">작업</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((statement) => {
                  const target = targetByEmployee.get(statement.employee_no)
                  return (
                    <tr key={statement.statement_id} aria-selected={statement.statement_id === selectedId}>
                      <th scope="row">
                        {statement.employee.name ?? statement.employee_no}
                        <span className={styles.subtext}>{target?.dept_name ?? "부서 미지정"} · #{statement.employee_no}</span>
                      </th>
                      <td>{statement.year}.{String(statement.month).padStart(2, "0")}</td>
                      <td className={styles.amount}>{won(statement.net_pay)}</td>
                      <td><Badge tone={statusTone(statement.status)}>{statement.status}</Badge></td>
                      <td>
                        <span className={styles.row}>
                          <Button size="small" variant={statement.statement_id === selectedId ? "primary" : "secondary"} onClick={() => select(statement)}>
                            {statement.status === "작성중" ? "편집" : "보기"}
                          </Button>
                          <Button size="small" variant="ghost" onClick={() => setHistoryFor(statement)}>이력</Button>
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </Table>
          )}
        </Card>

        <div className={styles.stack}>
          {notice && <Alert tone={notice.tone}>{notice.text}</Alert>}
          {!selected && <EmptyState title="정산을 선택하세요">목록에서 편집하거나 볼 급여를 고르면 여기에 표시됩니다.</EmptyState>}
          {selected && !editor && (
            <PayslipView
              statement={selected}
              components={data.components}
              printing={printingId === selected.statement_id}
              actions={selected.status === "작성중" ? (
                <>
                  <Button
                    disabled={isOwn}
                    title={isOwn ? "본인 급여는 다른 급여담당자가 수정해야 합니다." : undefined}
                    onClick={() => setEditor({ statementId: selected.statement_id, paymentDate: selected.payment_date, amounts: amountValuesFromItems(selected.items) })}
                  >
                    지급일·구성항목 편집
                  </Button>
                  <a href={routeHref({ moduleId: "payroll", screenId: "payroll-confirm", search: `period=${periodKey(selected)}` })}>확정 화면으로 이동</a>
                </>
              ) : (
                <>
                  <Button variant="secondary" onClick={() => print(selected.statement_id)}>PDF 저장·인쇄</Button>
                  <Button variant="secondary" onClick={() => void saveExcel(selected)}>엑셀 저장</Button>
                  <span className={styles.hint}>확정된 급여는 &lsquo;급여 확정·정정&rsquo;에서 확정취소 후 수정할 수 있습니다.</span>
                </>
              )}
            />
          )}
          {selected && editor?.statementId === selected.statement_id && (
            <Card title={`${selected.employee.name ?? selected.employee_no} · ${selected.year}년 ${selected.month}월 편집`}>
              <div className={styles.stack}>
                <TextInput
                  label="지급일"
                  type="date"
                  required
                  value={editor.paymentDate}
                  disabled={pending}
                  onChange={(event) => setEditor({ ...editor, paymentDate: event.target.value })}
                />
                <AmountFields
                  components={data.components}
                  values={editor.amounts}
                  disabled={pending}
                  onChange={(code, value) => setEditor({ ...editor, amounts: { ...editor.amounts, [code]: value } })}
                />
                <div className={styles.formFooter}>
                  <Button variant="secondary" disabled={pending} onClick={() => setEditor(null)}>취소</Button>
                  <Button pending={pending} onClick={() => void save()}>저장</Button>
                </div>
              </div>
            </Card>
          )}
        </div>
      </div>
      <HistoryDrawer statement={historyFor} onClose={() => setHistoryFor(null)} />
    </div>
  )
}
