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
import { loadWorkforce } from "../api/workforce"
import type { CurrentUser } from "../types/auth"
import type { PayrollComponent, PayrollHistoryEntry, PayrollItem, PayrollStatement } from "../types/payroll"
import type { DepartmentSummary, EmployeeSummary } from "../types/workforce"

type PayrollPanelProps = {
  enabled: boolean
  currentUser: CurrentUser
}

type AmountValues = Record<string, string>

const currentYear = new Date().getFullYear()
const currentMonth = new Date().getMonth() + 1

function amountValuesFromItems(items: PayrollItem[]): AmountValues {
  const values: AmountValues = {}
  for (const item of items) values[item.component_code] = String(item.amount)
  return values
}

function itemsFromAmountValues(values: AmountValues): Pick<PayrollItem, "component_code" | "amount">[] {
  return Object.entries(values)
    .filter(([, amount]) => amount.trim() !== "")
    .map(([component_code, amount]) => ({ component_code, amount: Number(amount) }))
}

function won(value: number): string {
  return value.toLocaleString("ko-KR")
}

type ComponentAmountFieldsProps = {
  components: PayrollComponent[]
  values: AmountValues
  onChange: (code: string, value: string) => void
}

function ComponentAmountFields({ components, values, onChange }: ComponentAmountFieldsProps) {
  const earnings = components.filter((item) => item.category === "지급")
  const deductions = components.filter((item) => item.category === "공제")
  return (
    <div className="payroll-component-fields">
      <fieldset>
        <legend>지급 항목</legend>
        {earnings.map((component) => (
          <label key={component.code}>
            {component.name}
            <input
              type="number"
              min="0"
              placeholder="미입력 시 저장하지 않음"
              value={values[component.code] ?? ""}
              onChange={(event) => onChange(component.code, event.target.value)}
            />
          </label>
        ))}
      </fieldset>
      <fieldset>
        <legend>공제 항목</legend>
        {deductions.map((component) => (
          <label key={component.code}>
            {component.name}
            <input
              type="number"
              min="0"
              placeholder="미입력 시 저장하지 않음"
              value={values[component.code] ?? ""}
              onChange={(event) => onChange(component.code, event.target.value)}
            />
          </label>
        ))}
      </fieldset>
    </div>
  )
}

type PayslipTableProps = {
  statement: PayrollStatement
  componentName: (code: string) => string
}

function PayslipTable({ statement, componentName }: PayslipTableProps) {
  const earnings = statement.items.filter((item) => item.category === "지급")
  const deductions = statement.items.filter((item) => item.category === "공제")
  const rowCount = Math.max(earnings.length, deductions.length, 1)
  const rows = Array.from({ length: rowCount }, (_, index) => ({
    earning: earnings[index],
    deduction: deductions[index],
  }))

  return (
    <table className="payslip-table">
      <thead>
        <tr>
          <th>지급내역 (A)</th>
          <th>지급액</th>
          <th>공제내역 (B)</th>
          <th>공제액</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row, index) => (
          <tr key={index}>
            <td>{row.earning ? componentName(row.earning.component_code) : ""}</td>
            <td>{row.earning ? `${won(row.earning.amount)}원` : ""}</td>
            <td>{row.deduction ? componentName(row.deduction.component_code) : ""}</td>
            <td>{row.deduction ? `${won(row.deduction.amount)}원` : ""}</td>
          </tr>
        ))}
      </tbody>
      <tfoot>
        <tr>
          <td>지급총액</td>
          <td>{won(statement.total_earnings)}원</td>
          <td>공제액 계</td>
          <td>{won(statement.total_deductions)}원</td>
        </tr>
        <tr className="payslip-net">
          <td colSpan={3}>차인지급액 (C)</td>
          <td>{won(statement.net_pay)}원</td>
        </tr>
      </tfoot>
    </table>
  )
}

export function PayrollPanel({ enabled, currentUser }: PayrollPanelProps) {
  const isPayrollManager = currentUser.is_superuser || currentUser.roles.includes("PAYROLL_MANAGER")
  const [tab, setTab] = useState<"mine" | "manage">("mine")
  const [components, setComponents] = useState<PayrollComponent[]>([])
  const [employees, setEmployees] = useState<EmployeeSummary[]>([])
  const [departments, setDepartments] = useState<DepartmentSummary[]>([])
  const [mine, setMine] = useState<PayrollStatement[]>([])
  const [managed, setManaged] = useState<PayrollStatement[]>([])
  const [filterDeptNo, setFilterDeptNo] = useState("")
  const [filterEmpNo, setFilterEmpNo] = useState("")
  const [createDeptNo, setCreateDeptNo] = useState("")
  const [createEmpNo, setCreateEmpNo] = useState("")
  const [createYear, setCreateYear] = useState(String(currentYear))
  const [createMonth, setCreateMonth] = useState(String(currentMonth))
  const [createItemValues, setCreateItemValues] = useState<AmountValues>({})
  const [itemDrafts, setItemDrafts] = useState<Record<number, AmountValues>>({})
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
        const workforce = await loadWorkforce()
        setEmployees(workforce.employees)
        setDepartments(workforce.departments)
        const managedList = filterEmpNo
          ? await loadPayrollStatementsForEmployee(Number(filterEmpNo))
          : await loadAllPayrollStatements()
        setManaged(managedList)
      }
      setMessage("")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "급여 정보를 불러오지 못했습니다.")
    } finally {
      setLoading(false)
    }
  }, [enabled, filterEmpNo, isPayrollManager])

  useEffect(() => {
    if (!enabled) return
    const timer = window.setTimeout(() => void refresh(), 0)
    return () => window.clearTimeout(timer)
  }, [enabled, refresh])

  const componentName = useCallback(
    (code: string) => components.find((item) => item.code === code)?.name ?? code,
    [components],
  )

  const employeesInDepartment = useCallback(
    (deptNo: string) => employees.filter((employee) => String(employee.dept_no ?? "") === deptNo),
    [employees],
  )

  function updateCreateItem(code: string, value: string) {
    setCreateItemValues((previous) => ({ ...previous, [code]: value }))
  }

  async function submitCreate(event: FormEvent) {
    event.preventDefault()
    if (!createEmpNo) {
      setMessage("부서와 사람을 선택해주세요.")
      return
    }
    setLoading(true)
    try {
      await createPayrollStatement(
        Number(createEmpNo),
        Number(createYear),
        Number(createMonth),
        itemsFromAmountValues(createItemValues),
      )
      setCreateItemValues({})
      setCreateEmpNo("")
      await refresh()
      setMessage("급여를 생성했습니다.")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "급여를 생성하지 못했습니다.")
    } finally {
      setLoading(false)
    }
  }

  function beginEditItems(statement: PayrollStatement) {
    setItemDrafts((previous) => ({ ...previous, [statement.statement_id]: amountValuesFromItems(statement.items) }))
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
      setMessage("구성항목을 최소 1건 이상 입력해야 합니다.")
      return
    }
    setLoading(true)
    try {
      await updatePayrollItems(statementId, items)
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

  const createCandidates = useMemo(() => employeesInDepartment(createDeptNo), [employeesInDepartment, createDeptNo])
  const filterCandidates = useMemo(() => employeesInDepartment(filterDeptNo), [employeesInDepartment, filterDeptNo])

  return (
    <section className="payroll-panel">
      {message && (
        <div className="notice" role="status">
          {message}
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
          <form className="department-form payroll-create-form" onSubmit={submitCreate}>
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
                <input
                  required
                  type="number"
                  value={createYear}
                  onChange={(event) => setCreateYear(event.target.value)}
                />
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
            <ComponentAmountFields components={components} values={createItemValues} onChange={updateCreateItem} />
            <button className="primary" disabled={loading} type="submit">
              급여 생성
            </button>
          </form>
          <div className="workforce-toolbar payroll-filter-toolbar">
            <div>
              <p className="step">FILTER</p>
              <h3>부서·사람으로 조회</h3>
            </div>
            <select
              aria-label="부서 필터"
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
            </select>
            <select
              aria-label="사람 필터"
              value={filterEmpNo}
              onChange={(event) => setFilterEmpNo(event.target.value)}
            >
              <option value="">전체 사람</option>
              {filterCandidates.map((employee) => (
                <option key={employee.emp_no} value={employee.emp_no}>
                  {employee.name} ({employee.emp_no})
                </option>
              ))}
            </select>
            <button className="refresh" type="button" disabled={loading} onClick={() => void refresh()}>
              새로고침
            </button>
          </div>
        </>
      )}

      <div className="request-list">
        {visible.length === 0 && <div className="empty">표시할 급여가 없습니다.</div>}
        {visible.map((item) => (
          <article className="payslip" key={item.statement_id}>
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
            <PayslipTable statement={item} componentName={componentName} />

            {tab === "manage" && isPayrollManager && item.status === "작성중" && !itemDrafts[item.statement_id] && (
              <div className="actions">
                <button onClick={() => beginEditItems(item)} type="button">
                  구성항목 편집
                </button>
                <button className="accent" onClick={() => void confirm(item.statement_id)} type="button">
                  확정
                </button>
              </div>
            )}

            {tab === "manage" && isPayrollManager && item.status === "확정" && (
              <div className="actions">
                <button onClick={() => void cancelConfirmation(item.statement_id)} type="button">
                  확정취소
                </button>
              </div>
            )}

            {itemDrafts[item.statement_id] && (
              <div className="payroll-items-editor">
                <ComponentAmountFields
                  components={components}
                  values={itemDrafts[item.statement_id]}
                  onChange={(code, value) => updateDraftItem(item.statement_id, code, value)}
                />
                <div className="actions">
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
                {(histories[item.statement_id] ?? []).map((entry) => (
                  <li key={entry.history_id}>
                    <strong>{entry.action}</strong> · {new Date(entry.changed_at).toLocaleString("ko-KR")} · 처리자{" "}
                    {entry.actor_employee_no}
                    {entry.reason && <span> · {entry.reason}</span>}
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
