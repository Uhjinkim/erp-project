import { FormEvent, useCallback, useEffect, useMemo, useState } from "react"

import { createDepartment, getEmployeeDetail, getMyEmployeeInfo, loadWorkforce } from "../api/workforce"
import type { CurrentUser } from "../types/auth"
import type {
  DepartmentSummary,
  EmployeeDetail,
  EmployeeSummary,
  PositionSummary,
} from "../types/workforce"
import { EmployeeInfoCard } from "./EmployeeInfoCard"
import { ChangeRequestApprovals, PersonalInfoEditor } from "./PersonalInfoRequests"

type WorkforcePanelProps = {
  enabled: boolean
  currentUser: CurrentUser
}

export function WorkforcePanel({ enabled, currentUser }: WorkforcePanelProps) {
  const [employees, setEmployees] = useState<EmployeeSummary[]>([])
  const [departments, setDepartments] = useState<DepartmentSummary[]>([])
  const [positions, setPositions] = useState<PositionSummary[]>([])
  const [search, setSearch] = useState("")
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(false)
  const [deptNo, setDeptNo] = useState("")
  const [deptName, setDeptName] = useState("")
  const [myInfo, setMyInfo] = useState<EmployeeDetail | null>(null)
  const [selectedEmployee, setSelectedEmployee] = useState<EmployeeDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  // 화면 분기용 안내일 뿐이며, 조회 권한은 백엔드가 HR-001에 따라 검사한다.
  const isHRManager = currentUser.is_superuser || currentUser.roles.includes("HR_MANAGER")
  const hasEmployee = currentUser.employee !== null

  const refresh = useCallback(async () => {
    if (!enabled) return
    setLoading(true)
    try {
      const [result, info] = await Promise.all([
        loadWorkforce(isHRManager),
        hasEmployee ? getMyEmployeeInfo() : Promise.resolve(null),
      ])
      setEmployees(result.employees)
      setDepartments(result.departments)
      setPositions(result.positions)
      setMyInfo(info)
      setMessage("")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "사원 정보를 불러오지 못했습니다.")
    } finally {
      setLoading(false)
    }
  }, [enabled, hasEmployee, isHRManager])

  async function selectEmployee(empNo: number) {
    setDetailLoading(true)
    try {
      setSelectedEmployee(await getEmployeeDetail(empNo))
      setMessage("")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "사원 상세 정보를 불러오지 못했습니다.")
    } finally {
      setDetailLoading(false)
    }
  }

  useEffect(() => {
    if (!enabled) return
    const timer = window.setTimeout(() => void refresh(), 0)
    return () => window.clearTimeout(timer)
  }, [enabled, refresh])

  const filteredEmployees = useMemo(() => {
    const keyword = search.trim().toLowerCase()
    if (!keyword) return employees
    return employees.filter((employee) =>
      employee.name.toLowerCase().includes(keyword)
      || employee.email?.toLowerCase().includes(keyword)
      || String(employee.emp_no).includes(keyword),
    )
  }, [employees, search])

  async function submitDepartment(event: FormEvent) {
    event.preventDefault()
    setLoading(true)
    try {
      await createDepartment(Number(deptNo), deptName)
      setDeptNo("")
      setDeptName("")
      await refresh()
      setMessage("부서를 등록했습니다.")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "부서를 등록하지 못했습니다.")
    } finally {
      setLoading(false)
    }
  }

  const departmentName = (departmentNo: number | null) =>
    departments.find((department) => department.dept_no === departmentNo)?.dept_name ?? "미배정"
  const positionName = (positionCode: string | null) =>
    positions.find((position) => position.position_code === positionCode)?.position_name ?? "미배정"

  return (
    <section className="workforce-panel">
      {message && <div className="notice" role="status">{message}</div>}
      <div className="workforce-toolbar">
        <div><p className="step">ORGANIZATION</p><h2>사원과 부서</h2></div>
        {isHRManager
          ? <input
              aria-label="사원 검색"
              placeholder="이름, 이메일, 사번 검색"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          : <span />}
        <button className="refresh" type="button" disabled={loading || !enabled} onClick={() => void refresh()}>새로고침</button>
      </div>
      <EmployeeInfoCard
        title={selectedEmployee ? "사원 인사 정보" : "내 인사 정보"}
        employee={selectedEmployee ?? myInfo}
        loading={loading || detailLoading}
        onBack={selectedEmployee ? () => setSelectedEmployee(null) : undefined}
      />
      {!selectedEmployee && myInfo && (
        <PersonalInfoEditor key={myInfo.emp_no} employee={myInfo} onContactUpdated={setMyInfo} />
      )}
      {isHRManager && <ChangeRequestApprovals onProcessed={() => void refresh()} />}
      <div className={`workforce-grid${isHRManager ? "" : " single"}`}>
        {isHRManager && <section className="list-panel">
          <h3>사원 <b>{filteredEmployees.length}</b></h3>
          <div className="employee-list">
            {filteredEmployees.map((employee) => (
              <button
                className={`employee-item${selectedEmployee?.emp_no === employee.emp_no ? " selected" : ""}`}
                key={employee.emp_no}
                type="button"
                aria-pressed={selectedEmployee?.emp_no === employee.emp_no}
                disabled={detailLoading}
                onClick={() => void selectEmployee(employee.emp_no)}
              >
                <div><strong>{employee.name}</strong><span>#{employee.emp_no}</span></div>
                <p>{departmentName(employee.dept_no)} · {positionName(employee.position_code)}</p>
                <small>{employee.email ?? "이메일 미등록"} · {employee.tenure_status}</small>
              </button>
            ))}
            {filteredEmployees.length === 0 && <div className="empty">표시할 사원이 없습니다.</div>}
          </div>
        </section>}
        <section className="list-panel">
          <h3>부서 <b>{departments.length}</b></h3>
          <div className="department-list">
            {departments.map((department) => (
              <article className="department-item" key={department.dept_no}>
                <strong>{department.dept_name}</strong>
                <span>#{department.dept_no}</span>
                <small>부서장 {department.head_emp_no ?? "미지정"}</small>
              </article>
            ))}
          </div>
          {isHRManager && (
            <form className="department-form" onSubmit={submitDepartment}>
              <h3>최상위 부서 등록</h3>
              <input required min="1" type="number" placeholder="부서번호" value={deptNo} onChange={(event) => setDeptNo(event.target.value)} />
              <input required placeholder="부서명" value={deptName} onChange={(event) => setDeptName(event.target.value)} />
              <button className="primary" disabled={loading} type="submit">부서 등록</button>
            </form>
          )}
        </section>
      </div>
    </section>
  )
}
