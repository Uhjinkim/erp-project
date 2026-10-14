import { useCallback, useState } from "react"
import type { FormEvent } from "react"
import { assignEmployeeRole, getEmployeeDetail, listEmployeeRoles, listEmployees, revokeEmployeeRole } from "../../../api/workforce"
import { Alert, Badge, Button, Card, ConfirmDialog, Select, Table } from "../../../components/ui"
import type { EmployeeDetail, EmployeeRoleAssignment } from "../../../types/workforce"
import { EmployeeLookup } from "../components/EmployeeLookup"
import type { LookupRow } from "../components/EmployeeLookup"
import { EmployeeSummary } from "../components/EmployeeSummary"
import { QueryFallback } from "../components/QueryFallback"
import type { MasterData } from "../hooks"
import { useMutation, useWorkforceQuery } from "../hooks"
import { assignableRoles, departmentLabel, formatDateTime, parseId, positionLabel, roleLabel, workforceHref } from "../model"
import styles from "../workforce.module.css"

// Query key: empNo. 계정 편집은 system 모듈, 역할 판정·중복 거절은 서버가 담당한다.
export function RoleGrantScreen({ enabled, search, master }: { enabled: boolean; search: URLSearchParams; master: MasterData }) {
  const empNo = parseId(search.get("empNo"))
  const loadEmployees = useCallback(async (keyword: string): Promise<LookupRow[]> => {
    const rows = await listEmployees({ search: keyword })
    return rows.map((row) => ({
      emp_no: row.emp_no, name: row.name, status: row.tenure_status,
      organization: `${departmentLabel(master.departments, row.dept_no)} · ${positionLabel(master.positions, row.position_code)}`,
      dates: `${row.hire_date} 입사`,
    }))
  }, [master])
  if (empNo === null) {
    return <EmployeeLookup title="역할 관리 대상 선택" description="재직 중인 사원에게만 새 역할을 부여할 수 있습니다." enabled={enabled} load={loadEmployees} hrefFor={(row) => workforceHref("role-grant", { empNo: row.emp_no })} actionLabel="역할 관리" />
  }
  return <RoleGrantView empNo={empNo} enabled={enabled} master={master} />
}

function RoleGrantView({ empNo, enabled, master }: { empNo: number; enabled: boolean; master: MasterData }) {
  const loadDetail = useCallback(() => getEmployeeDetail(empNo), [empNo])
  const loadRoles = useCallback(() => listEmployeeRoles(empNo), [empNo])
  const detail = useWorkforceQuery(enabled, loadDetail)
  const roles = useWorkforceQuery(enabled, loadRoles)
  const [notice, setNotice] = useState("")
  if (!detail.data) return <QueryFallback query={detail} label="사원 정보를 불러오는 중" />

  const changed = (message: string) => {
    setNotice(message)
    void roles.reload()
  }
  return (
    <div className={styles.stack}>
      <Card title="대상 사원" actions={<a href={workforceHref("employee-detail", { empNo })}>사원 상세</a>}>
        <EmployeeSummary employee={detail.data} />
      </Card>
      {notice && <Alert tone="success">{notice}</Alert>}
      <QueryFallback query={roles} label="역할을 불러오는 중" />
      {roles.data && (
        <>
          <AssignForm employee={detail.data} assignments={roles.data} master={master} onDone={(code) => changed(`${roleLabel(master.roles, code)} 역할을 부여했습니다.`)} />
          <AssignmentTable empNo={empNo} assignments={roles.data} master={master} loading={roles.loading} onReload={() => void roles.reload()} onRevoked={(code) => changed(`${roleLabel(master.roles, code)} 역할을 회수했습니다.`)} />
        </>
      )}
    </div>
  )
}

function AssignForm({ employee, assignments, master, onDone }: { employee: EmployeeDetail; assignments: EmployeeRoleAssignment[]; master: MasterData; onDone: (code: string) => void }) {
  const [roleCode, setRoleCode] = useState("")
  const mutation = useMutation()
  const options = assignableRoles(master.roles, assignments)

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!roleCode) return
    const result = await mutation.run(() => assignEmployeeRole(employee.emp_no, roleCode))
    if (result) {
      setRoleCode("")
      onDone(result.role_code)
    }
  }

  if (employee.tenure_status !== "재직") {
    return <Alert tone="info">재직 중인 사원에게만 역할을 부여할 수 있습니다. 현재 상태: {employee.tenure_status}</Alert>
  }
  return (
    <Card title="역할 부여">
      <form className={styles.row} onSubmit={(event) => void submit(event)}>
        <Select label="부여할 역할" required value={roleCode} disabled={mutation.pending || options.length === 0} onChange={(event) => setRoleCode(event.target.value)}>
          <option value="">{options.length ? "선택" : "부여 가능한 역할 없음"}</option>
          {options.map((role) => <option key={role.role_code} value={role.role_code}>{role.role_name}</option>)}
        </Select>
        <Button type="submit" pending={mutation.pending} disabled={!roleCode}>부여</Button>
      </form>
      <p className={styles.hint}>휴가 승인 인사담당자 등 인원 제한이 있는 역할은 서버가 확인합니다. 여러 역할의 권한은 각각 독립적으로 적용됩니다.</p>
      {mutation.error && <Alert tone="error">{mutation.error}</Alert>}
    </Card>
  )
}

function AssignmentTable({ empNo, assignments, master, loading, onReload, onRevoked }: {
  empNo: number; assignments: EmployeeRoleAssignment[]; master: MasterData; loading: boolean; onReload: () => void; onRevoked: (code: string) => void
}) {
  const [target, setTarget] = useState<EmployeeRoleAssignment | null>(null)
  const mutation = useMutation()
  const sorted = [...assignments].sort((a, b) => Number(a.revoked_at !== null) - Number(b.revoked_at !== null) || b.assigned_at.localeCompare(a.assigned_at))

  async function revoke() {
    if (!target) return
    const result = await mutation.run(() => revokeEmployeeRole(empNo, target.employee_role_id))
    if (result) {
      setTarget(null)
      onRevoked(result.role_code)
    }
  }

  return (
    <Card title="역할 부여 이력" actions={<Button variant="secondary" size="small" pending={loading} onClick={onReload}>새로고침</Button>}>
      {mutation.error && !target && <Alert tone="error">{mutation.error}</Alert>}
      {sorted.length === 0
        ? <p className={styles.hint}>부여된 역할이 없습니다.</p>
        : <Table caption="역할 부여·회수 이력">
            <thead><tr><th scope="col">역할</th><th scope="col">상태</th><th scope="col">부여일시</th><th scope="col">회수일시</th><th scope="col">작업</th></tr></thead>
            <tbody>
              {sorted.map((item) => (
                <tr key={item.employee_role_id}>
                  <th scope="row">{roleLabel(master.roles, item.role_code)}</th>
                  <td><Badge tone={item.revoked_at ? "neutral" : "success"}>{item.revoked_at ? "회수" : "활성"}</Badge></td>
                  <td>{formatDateTime(item.assigned_at)}</td>
                  <td>{formatDateTime(item.revoked_at)}</td>
                  <td>{item.revoked_at === null
                    ? <Button size="small" variant="danger" onClick={() => { mutation.reset(); setTarget(item) }} aria-label={`${roleLabel(master.roles, item.role_code)} 회수`}>회수</Button>
                    : <span className={styles.subtext}>-</span>}</td>
                </tr>
              ))}
            </tbody>
          </Table>}
      <ConfirmDialog open={target !== null} danger title="역할 회수" confirmLabel="회수" busy={mutation.pending} onClose={() => setTarget(null)} onConfirm={() => void revoke()}>
        <p>{target && roleLabel(master.roles, target.role_code)} 역할을 회수합니다. 회수 이력은 보존됩니다.</p>
        {mutation.error && <Alert tone="error">{mutation.error}</Alert>}
      </ConfirmDialog>
    </Card>
  )
}
