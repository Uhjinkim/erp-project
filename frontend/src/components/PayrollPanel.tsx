import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react"

import {
  cancelPayrollConfirmation,
  confirmPayrollStatement,
  createPayrollStatement,
  downloadPayslipExcel,
  loadAllPayrollStatements,
  loadMyPayrollStatements,
  loadPayrollComponents,
  loadPayrollHistory,
  loadPayrollStatementsForEmployee,
  loadPayrollTargets,
  updatePayrollItems,
} from "../api/payroll"
import type { CurrentUser } from "../types/auth"
import type {
  PayrollComponent,
  PayrollHistoryEntry,
  PayrollItem,
  PayrollStatement,
  PayrollTargetEmployee,
} from "../types/payroll"

type PayrollPanelProps = {
  enabled: boolean
  currentUser: CurrentUser
}

type AmountValues = Record<string, string>
type Notice = { text: string; tone: "info" | "error" }
type StatusFilter = "all" | "작성중" | "확정" | "미작성"

type Department = { dept_no: number; dept_name: string }

const NO_DEPARTMENT = "__none__"

const today = new Date()
const currentYear = today.getFullYear()
const currentMonth = today.getMonth() + 1
const currentPeriod = `${currentYear}-${String(currentMonth).padStart(2, "0")}`

function periodKey(statement: PayrollStatement): string {
  return `${statement.year}-${String(statement.month).padStart(2, "0")}`
}

function amountValuesFromItems(items: PayrollItem[]): AmountValues {
  const values: AmountValues = {}
  for (const item of items) values[item.component_code] = String(Math.trunc(item.amount))
  return values
}

function itemsFromAmountValues(values: AmountValues): Pick<PayrollItem, "component_code" | "amount">[] {
  return Object.entries(values)
    .filter(([, amount]) => amount.trim() !== "")
    .map(([component_code, amount]) => ({ component_code, amount: Math.trunc(Number(amount)) }))
}

function won(value: number): string {
  return `${Math.trunc(value).toLocaleString("ko-KR")}원`
}

type ComponentAmountFieldsProps = {
  components: PayrollComponent[]
  values: AmountValues
  onChange: (code: string, value: string) => void
}

function ComponentAmountFields({ components, values, onChange }: ComponentAmountFieldsProps) {
  // Components arrive from the API already in payslip order.
  const groups: [string, PayrollComponent[]][] = [
    ["지급 항목", components.filter((item) => item.category === "지급")],
    ["공제 항목", components.filter((item) => item.category === "공제")],
  ]
  return (
    <div className="payroll-component-fields">
      {groups.map(([legend, items]) => (
        <fieldset key={legend}>
          <legend>{legend}</legend>
          {items.map((component) => (
            <label key={component.code}>
              {component.name}
              <input
                type="number"
                min="0"
                step="1"
                placeholder="미입력 시 저장하지 않음"
                value={values[component.code] ?? ""}
                onChange={(event) => onChange(component.code, event.target.value)}
              />
            </label>
          ))}
        </fieldset>
      ))}
    </div>
  )
}

type PayslipTableProps = {
  statement: PayrollStatement
  components: PayrollComponent[]
}

function PayslipTable({ statement, components }: PayslipTableProps) {
  // Only nonzero items are listed; the API returns items already in payslip order.
  const nameByCode = new Map(components.map((component) => [component.code, component.name]))
  const lines = statement.items
    .filter((item) => Math.trunc(item.amount) !== 0)
    .map((item) => ({
      name: nameByCode.get(item.component_code) ?? item.component_code,
      category: item.category,
      amount: item.amount,
    }))
  const earnings = lines.filter((line) => line.category === "지급")
  const deductions = lines.filter((line) => line.category === "공제")
  const rowCount = Math.max(earnings.length, deductions.length, 1)

  return (
    <table className="payslip-table">
      <thead>
        <tr>
          <th scope="col">지급내역 (A)</th>
          <th scope="col">지급액</th>
          <th scope="col">공제내역 (B)</th>
          <th scope="col">공제액</th>
        </tr>
      </thead>
      <tbody>
        {Array.from({ length: rowCount }, (_, index) => {
          const earning = earnings[index]
          const deduction = deductions[index]
          return (
            <tr key={index}>
              <td>{earning?.name ?? ""}</td>
              <td>{earning ? won(earning.amount) : ""}</td>
              <td>{deduction?.name ?? ""}</td>
              <td>{deduction ? won(deduction.amount) : ""}</td>
            </tr>
          )
        })}
      </tbody>
      <tfoot>
        <tr>
          <td>지급총액</td>
          <td>{won(statement.total_earnings)}</td>
          <td>공제액 계</td>
          <td>{won(statement.total_deductions)}</td>
        </tr>
        <tr className="payslip-net">
          <td colSpan={3}>차인지급액 (C)</td>
          <td>{won(statement.net_pay)}</td>
        </tr>
      </tfoot>
    </table>
  )
}

export function PayrollPanel({ enabled, currentUser }: PayrollPanelProps) {
  const isPayrollManager = currentUser.is_superuser || currentUser.roles.includes("PAYROLL_MANAGER")
  const ownEmployeeNo = currentUser.employee?.emp_no ?? null
  const createFormRef = useRef<HTMLFormElement>(null)
  const [tab, setTab] = useState<"mine" | "manage">("mine")
  const [components, setComponents] = useState<PayrollComponent[]>([])
  const [employees, setEmployees] = useState<PayrollTargetEmployee[]>([])
  const [mine, setMine] = useState<PayrollStatement[]>([])
  const [managed, setManaged] = useState<PayrollStatement[]>([])
  const [filterDeptNo, setFilterDeptNo] = useState("")
  const [filterEmpNo, setFilterEmpNo] = useState("")
  const [filterPeriod, setFilterPeriod] = useState(currentPeriod)
  const [filterStatus, setFilterStatus] = useState<StatusFilter>("all")
  const [createDeptNo, setCreateDeptNo] = useState("")
  const [createEmpNo, setCreateEmpNo] = useState("")
  const [createYear, setCreateYear] = useState(String(currentYear))
  const [createMonth, setCreateMonth] = useState(String(currentMonth))
  const [createItemValues, setCreateItemValues] = useState<AmountValues>({})
  // Empty means "let the backend apply the settlement-date policy".
  const [createPaymentDate, setCreatePaymentDate] = useState("")
  const [itemDrafts, setItemDrafts] = useState<Record<number, AmountValues>>({})
  const [paymentDateDrafts, setPaymentDateDrafts] = useState<Record<number, string>>({})
  const [printingId, setPrintingId] = useState<number | null>(null)
  const [histories, setHistories] = useState<Record<number, PayrollHistoryEntry[]>>({})
  const [openHistory, setOpenHistory] = useState<number | null>(null)
  const [notice, setNotice] = useState<Notice | null>(null)
  const [loading, setLoading] = useState(false)

  const showInfo = useCallback((text: string) => setNotice({ text, tone: "info" }), [])
  const showError = useCallback((error: unknown, fallback: string) => {
    setNotice({ text: error instanceof Error ? error.message : fallback, tone: "error" })
    window.scrollTo({ top: 0, behavior: "smooth" })
  }, [])

  const refresh = useCallback(async () => {
    if (!enabled) return
    setLoading(true)
    try {
      const [componentList, mineList] = await Promise.all([loadPayrollComponents(), loadMyPayrollStatements()])
      setComponents(componentList)
      setMine(mineList)
      if (isPayrollManager) {
        setEmployees(await loadPayrollTargets())
        const managedList = filterEmpNo
          ? await loadPayrollStatementsForEmployee(Number(filterEmpNo))
          : await loadAllPayrollStatements()
        setManaged(managedList)
      }
      setNotice(null)
    } catch (error) {
      showError(error, "급여 정보를 불러오지 못했습니다.")
    } finally {
      setLoading(false)
    }
  }, [enabled, filterEmpNo, isPayrollManager, showError])

  useEffect(() => {
    if (!enabled) return
    const timer = window.setTimeout(() => void refresh(), 0)
    return () => window.clearTimeout(timer)
  }, [enabled, refresh])

  // Print only the chosen payslip; the browser print dialog also offers "PDF로 저장".
  useEffect(() => {
    if (printingId === null) return
    const finish = () => setPrintingId(null)
    document.body.classList.add("payroll-printing")
    window.addEventListener("afterprint", finish, { once: true })
    const timer = window.setTimeout(() => window.print(), 0)
    return () => {
      window.clearTimeout(timer)
      window.removeEventListener("afterprint", finish)
      document.body.classList.remove("payroll-printing")
    }
  }, [printingId])

  async function saveExcel(statement: PayrollStatement) {
    try {
      await downloadPayslipExcel(statement)
    } catch (error) {
      showError(error, "급여명세서를 내려받지 못했습니다.")
    }
  }

  const departments = useMemo(() => {
    const byNo = new Map<number, Department>()
    for (const employee of employees) {
      if (employee.dept_no !== null && !byNo.has(employee.dept_no)) {
        byNo.set(employee.dept_no, { dept_no: employee.dept_no, dept_name: employee.dept_name ?? `${employee.dept_no}` })
      }
    }
    return [...byNo.values()].sort((left, right) => left.dept_name.localeCompare(right.dept_name, "ko"))
  }, [employees])

  const employeesInDepartment = useCallback(
    (deptNo: string) =>
      employees.filter((employee) =>
        deptNo === NO_DEPARTMENT ? employee.dept_no === null : String(employee.dept_no) === deptNo,
      ),
    [employees],
  )
  const hasUnassigned = employees.some((employee) => employee.dept_no === null)

  function updateCreateItem(code: string, value: string) {
    setCreateItemValues((previous) => ({ ...previous, [code]: value }))
  }

  async function submitCreate(event: FormEvent) {
    event.preventDefault()
    if (!createEmpNo) {
      showError(null, "부서와 사람을 선택해주세요.")
      return
    }
    setLoading(true)
    try {
      await createPayrollStatement(
        Number(createEmpNo),
        Number(createYear),
        Number(createMonth),
        itemsFromAmountValues(createItemValues),
        createPaymentDate || null,
      )
      setCreateItemValues({})
      setCreatePaymentDate("")
      setCreateEmpNo("")
      await refresh()
      showInfo("급여를 생성했습니다.")
    } catch (error) {
      showError(error, "급여를 생성하지 못했습니다.")
    } finally {
      setLoading(false)
    }
  }

  function prefillCreate(employee: PayrollTargetEmployee) {
    const [year, month] = filterPeriod.split("-")
    setCreateDeptNo(employee.dept_no === null ? NO_DEPARTMENT : String(employee.dept_no))
    setCreateEmpNo(String(employee.emp_no))
    setCreateYear(String(Number(year)))
    setCreateMonth(String(Number(month)))
    createFormRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
  }

  function beginEditItems(statement: PayrollStatement) {
    setItemDrafts((previous) => ({ ...previous, [statement.statement_id]: amountValuesFromItems(statement.items) }))
    setPaymentDateDrafts((previous) => ({ ...previous, [statement.statement_id]: statement.payment_date }))
  }

  function closeEditor(statementId: number) {
    setItemDrafts((previous) => {
      const next = { ...previous }
      delete next[statementId]
      return next
    })
    setPaymentDateDrafts((previous) => {
      const next = { ...previous }
      delete next[statementId]
      return next
    })
  }

  function updateDraftItem(statementId: number, code: string, value: string) {
    setItemDrafts((previous) => ({
      ...previous,
      [statementId]: { ...(previous[statementId] ?? {}), [code]: value },
    }))
  }

  async function saveItems(statementId: number) {
    const items = itemsFromAmountValues(itemDrafts[statementId] ?? {})
    if (items.length === 0) {
      showError(null, "구성항목을 최소 1건 이상 입력해야 합니다.")
      return
    }
    setLoading(true)
    try {
      await updatePayrollItems(statementId, items, paymentDateDrafts[statementId] || null)
      closeEditor(statementId)
      setHistories((previous) => ({ ...previous, [statementId]: [] }))
      setOpenHistory(null)
      await refresh()
      showInfo("급여 내용을 저장했습니다.")
    } catch (error) {
      showError(error, "구성항목을 저장하지 못했습니다.")
    } finally {
      setLoading(false)
    }
  }

  async function confirm(statementId: number) {
    setLoading(true)
    try {
      await confirmPayrollStatement(statementId)
      setOpenHistory(null)
      await refresh()
      showInfo("급여를 확정했습니다.")
    } catch (error) {
      showError(error, "확정하지 못했습니다.")
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
      setOpenHistory(null)
      await refresh()
      showInfo("확정을 취소했습니다.")
    } catch (error) {
      showError(error, "확정취소하지 못했습니다.")
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
      showError(error, "이력을 불러오지 못했습니다.")
    }
  }

  const createCandidates = useMemo(() => employeesInDepartment(createDeptNo), [employeesInDepartment, createDeptNo])
  const filterCandidates = useMemo(
    () => (filterDeptNo ? employeesInDepartment(filterDeptNo) : employees),
    [employeesInDepartment, employees, filterDeptNo],
  )

  // Statements within the selected department/person/period, before the status filter.
  const scopedStatements = useMemo(() => {
    const allowed = filterDeptNo ? new Set(filterCandidates.map((employee) => employee.emp_no)) : null
    return managed.filter(
      (statement) =>
        (!allowed || allowed.has(statement.employee_no)) && (!filterPeriod || periodKey(statement) === filterPeriod),
    )
  }, [filterCandidates, filterDeptNo, filterPeriod, managed])

  const missingEmployees = useMemo(() => {
    if (!filterPeriod) return []
    const scope = filterEmpNo
      ? employees.filter((employee) => String(employee.emp_no) === filterEmpNo)
      : filterCandidates
    const written = new Set(scopedStatements.map((statement) => statement.employee_no))
    return scope.filter((employee) => employee.is_active && !written.has(employee.emp_no))
  }, [employees, filterCandidates, filterEmpNo, filterPeriod, scopedStatements])

  const draftCount = scopedStatements.filter((statement) => statement.status === "작성중").length
  const confirmedCount = scopedStatements.filter((statement) => statement.status === "확정").length
  const managedVisible =
    filterStatus === "all" || filterStatus === "미작성"
      ? scopedStatements
      : scopedStatements.filter((statement) => statement.status === filterStatus)
  const visible = tab === "mine" ? mine : managedVisible

  return (
    <section className="payroll-panel">
      {notice && (
        <div
          className={notice.tone === "error" ? "notice notice--error payroll-alert" : "notice"}
          role={notice.tone === "error" ? "alert" : "status"}
        >
          <span>{notice.tone === "error" ? `⚠ ${notice.text}` : notice.text}</span>
          <button type="button" className="notice-close" aria-label="알림 닫기" onClick={() => setNotice(null)}>
            ×
          </button>
        </div>
      )}
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
          <form ref={createFormRef} className="department-form payroll-create-form" onSubmit={submitCreate}>
            <h3>급여 생성</h3>
            <div className="two-columns">
              <label>
                부서
                <select
                  value={createDeptNo}
                  onChange={(event) => {
                    setCreateDeptNo(event.target.value)
                    setCreateEmpNo("")
                  }}
                >
                  <option value="">부서 선택</option>
                  {departments.map((department) => (
                    <option key={department.dept_no} value={department.dept_no}>
                      {department.dept_name}
                    </option>
                  ))}
                  {hasUnassigned && <option value={NO_DEPARTMENT}>부서 미지정</option>}
                </select>
              </label>
              <label>
                사람
                <select
                  required
                  disabled={!createDeptNo}
                  value={createEmpNo}
                  onChange={(event) => setCreateEmpNo(event.target.value)}
                >
                  <option value="">{createDeptNo ? "사람 선택" : "부서를 먼저 선택하세요"}</option>
                  {createCandidates.map((employee) => (
                    <option key={employee.emp_no} value={employee.emp_no}>
                      {employee.name} ({employee.emp_no})
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="two-columns">
              <label>
                정산연도
                <input required type="number" value={createYear} onChange={(event) => setCreateYear(event.target.value)} />
              </label>
              <label>
                정산월
                <input
                  required
                  type="number"
                  min="1"
                  max="12"
                  value={createMonth}
                  onChange={(event) => setCreateMonth(event.target.value)}
                />
              </label>
            </div>
            <label>
              지급일 (선택)
              <input
                type="date"
                value={createPaymentDate}
                onChange={(event) => setCreatePaymentDate(event.target.value)}
                aria-describedby="payroll-payment-date-help"
              />
            </label>
            <p className="helper" id="payroll-payment-date-help">
              비워 두면 매월 25일(주말·공휴일이면 직전 평일)로 자동 지정되며, 생성 후에도 작성중 상태에서 수정할 수 있습니다.
            </p>
            <ComponentAmountFields components={components} values={createItemValues} onChange={updateCreateItem} />
            <button className="primary" disabled={loading} type="submit">
              급여 생성
            </button>
          </form>

          <div className="payroll-filter">
            <div className="payroll-filter-heading">
              <div>
                <p className="step">FILTER</p>
                <h3>부서·사람·상태로 조회</h3>
              </div>
              <button className="refresh" type="button" disabled={loading} onClick={() => void refresh()}>
                새로고침
              </button>
            </div>
            <div className="payroll-filter-controls">
              <label>
                부서
                <select
                  value={filterDeptNo}
                  onChange={(event) => {
                    setFilterDeptNo(event.target.value)
                    setFilterEmpNo("")
                  }}
                >
                  <option value="">전체 부서</option>
                  {departments.map((department) => (
                    <option key={department.dept_no} value={department.dept_no}>
                      {department.dept_name}
                    </option>
                  ))}
                  {hasUnassigned && <option value={NO_DEPARTMENT}>부서 미지정</option>}
                </select>
              </label>
              <label>
                사람
                <select value={filterEmpNo} onChange={(event) => setFilterEmpNo(event.target.value)}>
                  <option value="">전체 사람</option>
                  {filterCandidates.map((employee) => (
                    <option key={employee.emp_no} value={employee.emp_no}>
                      {employee.name} ({employee.emp_no})
                    </option>
                  ))}
                </select>
              </label>
              <label>
                정산월
                <input type="month" value={filterPeriod} onChange={(event) => setFilterPeriod(event.target.value)} />
              </label>
              <label>
                상태
                <select value={filterStatus} onChange={(event) => setFilterStatus(event.target.value as StatusFilter)}>
                  <option value="all">전체</option>
                  <option value="작성중">작성중 (확정 필요)</option>
                  <option value="확정">확정</option>
                  <option value="미작성">미작성</option>
                </select>
              </label>
            </div>
            {filterPeriod && (
              <div className="payroll-status-summary" aria-label="선택한 정산월 처리 현황">
                <button type="button" onClick={() => setFilterStatus("작성중")}>
                  작성중(확정 필요) <b>{draftCount}</b>
                </button>
                <button type="button" onClick={() => setFilterStatus("미작성")}>
                  미작성 <b>{missingEmployees.length}</b>
                </button>
                <button type="button" onClick={() => setFilterStatus("확정")}>
                  확정 <b>{confirmedCount}</b>
                </button>
              </div>
            )}
          </div>
        </>
      )}

      {tab === "manage" && isPayrollManager && filterStatus === "미작성" ? (
        <div className="request-list">
          {!filterPeriod && <div className="empty">미작성 대상을 보려면 정산월을 선택하세요.</div>}
          {filterPeriod && missingEmployees.length === 0 && (
            <div className="empty">선택한 정산월에 급여가 없는 재직 사원이 없습니다.</div>
          )}
          {filterPeriod && missingEmployees.length > 0 && (
            <ul className="payroll-missing-list">
              {missingEmployees.map((employee) => {
                const isSelf = employee.emp_no === ownEmployeeNo
                return (
                  <li key={employee.emp_no}>
                    <div>
                      <strong>{employee.name}</strong>
                      <span>
                        {employee.dept_name ?? "부서 미지정"} · #{employee.emp_no}
                      </span>
                    </div>
                    <button
                      type="button"
                      disabled={isSelf}
                      title={isSelf ? "본인 급여는 다른 급여담당자가 생성해야 합니다." : undefined}
                      onClick={() => prefillCreate(employee)}
                    >
                      {isSelf ? "본인(생성 불가)" : "급여 생성"}
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      ) : (
        <div className="request-list">
          {visible.length === 0 && <div className="empty">표시할 급여가 없습니다.</div>}
          {visible.map((item) => (
            <article
              className={printingId === item.statement_id ? "payslip payslip--printing" : "payslip"}
              key={item.statement_id}
            >
              <header className="payslip-header">
                <h3>
                  {item.year}년 {item.month}월 급여명세서
                </h3>
                <span className={`badge badge--payroll-${item.status}`}>{item.status}</span>
              </header>
              <dl className="payslip-meta">
                <div>
                  <dt>성명</dt>
                  <dd>{item.employee.name ?? "-"}</dd>
                </div>
                <div>
                  <dt>직급</dt>
                  <dd>{item.employee.position_name ?? "-"}</dd>
                </div>
                <div>
                  <dt>사번</dt>
                  <dd>{item.employee_no}</dd>
                </div>
                <div>
                  <dt>지급일</dt>
                  <dd>{item.payment_date}</dd>
                </div>
              </dl>
              <PayslipTable statement={item} components={components} />

              {tab === "manage" && item.status === "작성중" && !itemDrafts[item.statement_id] && (
                <div className="actions">
                  <button onClick={() => beginEditItems(item)} type="button">
                    지급일·구성항목 편집
                  </button>
                  <button className="accent" onClick={() => void confirm(item.statement_id)} type="button">
                    확정
                  </button>
                </div>
              )}

              {item.status === "확정" && (
                <div className="actions">
                  <button type="button" onClick={() => setPrintingId(item.statement_id)}>
                    PDF 저장·인쇄
                  </button>
                  <button type="button" onClick={() => void saveExcel(item)}>
                    엑셀 저장
                  </button>
                  {tab === "manage" && (
                    <button onClick={() => void cancelConfirmation(item.statement_id)} type="button">
                      확정취소
                    </button>
                  )}
                </div>
              )}

              {itemDrafts[item.statement_id] && (
                <div className="payroll-items-editor">
                  <label className="payroll-payment-date">
                    지급일
                    <input
                      type="date"
                      required
                      value={paymentDateDrafts[item.statement_id] ?? item.payment_date}
                      onChange={(event) =>
                        setPaymentDateDrafts((previous) => ({ ...previous, [item.statement_id]: event.target.value }))
                      }
                    />
                  </label>
                  <ComponentAmountFields
                    components={components}
                    values={itemDrafts[item.statement_id]}
                    onChange={(code, value) => updateDraftItem(item.statement_id, code, value)}
                  />
                  <div className="actions">
                    <button type="button" onClick={() => closeEditor(item.statement_id)}>
                      취소
                    </button>
                    <button className="accent" type="button" onClick={() => void saveItems(item.statement_id)}>
                      저장
                    </button>
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
                  {(histories[item.statement_id] ?? []).map((entry) => {
                    const detailed = entry.actor_name !== undefined
                    const changedAt = new Date(entry.changed_at)
                    return (
                      <li key={entry.history_id}>
                        <div className="payroll-history-head">
                          <strong>{entry.action}</strong>
                          <span>
                            {" / "}
                            {detailed ? changedAt.toLocaleString("ko-KR") : changedAt.toLocaleDateString("ko-KR")}
                          </span>
                          {detailed && <span> / {entry.actor_name ?? "알 수 없음"}</span>}
                        </div>
                        {detailed && entry.reason && <p className="payroll-history-detail">{entry.reason}</p>}
                      </li>
                    )
                  })}
                  {(histories[item.statement_id] ?? []).length === 0 && <li>이력이 없습니다.</li>}
                </ul>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
