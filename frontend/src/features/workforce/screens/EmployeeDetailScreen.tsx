import { useCallback, useState } from "react"
import { getEmployeeDetail, listEmployeeRoles } from "../../../api/workforce"
import { Badge, Button, Card, DetailList, EmptyState, Table, Tabs } from "../../../components/ui"
import { EmployeeSummary } from "../components/EmployeeSummary"
import { HistoryPanel } from "../components/HistoryPanel"
import { QueryFallback } from "../components/QueryFallback"
import type { MasterData } from "../hooks"
import { useWorkforceQuery } from "../hooks"
import { formatDateTime, genderLabel, maskAccount, parseId, roleLabel, workforceHref } from "../model"
import type { EmployeeDetail } from "../../../types/workforce"
import styles from "../workforce.module.css"

const tabs = [{ value: "info", label: "인사 정보" }, { value: "history", label: "인사 이력·발령" }, { value: "roles", label: "업무 역할" }]

// Query keys: empNo(필수), tab=info|history|roles.
export function EmployeeDetailScreen({ enabled, search, master }: { enabled: boolean; search: URLSearchParams; master: MasterData }) {
  const empNo = parseId(search.get("empNo"))
  if (empNo === null) {
    return <EmptyState title="사원을 선택하세요" action={<a href={workforceHref("employee-list")}>사원 목록으로 이동</a>}>상세 주소에는 사번(empNo)이 필요합니다.</EmptyState>
  }
  return <EmployeeDetailView empNo={empNo} enabled={enabled} tab={search.get("tab") ?? "info"} master={master} />
}

function EmployeeDetailView({ empNo, enabled, tab, master }: { empNo: number; enabled: boolean; tab: string; master: MasterData }) {
  const load = useCallback(() => getEmployeeDetail(empNo), [empNo])
  const detail = useWorkforceQuery(enabled, load)
  const selected = tabs.some((item) => item.value === tab) ? tab : "info"
  if (!detail.data) return <QueryFallback query={detail} label="사원 정보를 불러오는 중" />
  const employee = detail.data
  const retired = employee.tenure_status === "퇴사"

  return (
    <div className={styles.stack}>
      <Card title={`${employee.name} · 사번 ${employee.emp_no}`} actions={
        <span className={styles.links}>
          <a href={workforceHref("employee-list")}>목록</a>
          <a href={workforceHref("role-grant", { empNo })}>역할 관리</a>
          {retired
            ? <a href={workforceHref("rehire", { empNo })}>재입사 처리</a>
            : <a href={workforceHref("retire", { empNo })}>퇴사 처리</a>}
        </span>
      }>
        <EmployeeSummary employee={employee} />
        {detail.error && <p className={styles.hint} role="alert">최신 정보를 다시 불러오지 못했습니다: {detail.error}</p>}
      </Card>
      <Tabs label="사원 상세 구분" items={tabs} value={selected} onChange={(value) => { window.location.hash = workforceHref("employee-detail", { empNo, tab: value === "info" ? undefined : value }) }}>
        {selected === "info" && <InfoPanel employee={employee} />}
        {selected === "history" && <HistoryPanel employee={employee} master={master} enabled={enabled} onChanged={() => void detail.reload()} />}
        {selected === "roles" && <RolesSummary empNo={empNo} enabled={enabled} master={master} />}
      </Tabs>
    </div>
  )
}

function InfoPanel({ employee }: { employee: EmployeeDetail }) {
  const [showAccount, setShowAccount] = useState(false)
  return (
    <div className={styles.stack}>
      <Card title="인적사항·연락처">
        <DetailList items={[
          { key: "birth", label: "생년월일", value: employee.birth_date ?? "미등록" },
          { key: "gender", label: "성별", value: genderLabel(employee.gender) },
          { key: "email", label: "사내 이메일", value: employee.email ?? "미등록" },
          { key: "phone", label: "연락처", value: employee.phone ?? "미등록" },
          { key: "extension", label: "내선번호", value: employee.extension_no ?? "미등록" },
          { key: "address", label: "주소", value: employee.address ?? "미등록" },
        ]} />
        <p className={styles.hint}>연락처·주소·사내 이메일·급여계좌는 본인의 수정 요청 승인 후 변경됩니다.</p>
      </Card>
      <Card title="급여계좌" actions={employee.account_no && (
        <Button variant="ghost" size="small" aria-pressed={showAccount} onClick={() => setShowAccount(!showAccount)}>{showAccount ? "가리기" : "전체 보기"}</Button>
      )}>
        <DetailList items={[
          { key: "bank", label: "은행 코드", value: employee.bank_code ?? "미등록" },
          { key: "account", label: "계좌번호", value: showAccount ? employee.account_no ?? "미등록" : maskAccount(employee.account_no) },
        ]} />
      </Card>
    </div>
  )
}

function RolesSummary({ empNo, enabled, master }: { empNo: number; enabled: boolean; master: MasterData }) {
  const load = useCallback(() => listEmployeeRoles(empNo), [empNo])
  const roles = useWorkforceQuery(enabled, load)
  return (
    <Card title="업무 역할" actions={<a href={workforceHref("role-grant", { empNo })}>부여·회수</a>}>
      <QueryFallback query={roles} label="역할을 불러오는 중" />
      {roles.data && roles.data.length === 0 && <p className={styles.hint}>부여된 역할이 없습니다.</p>}
      {roles.data && roles.data.length > 0 && (
        <Table caption="역할 부여 이력">
          <thead><tr><th scope="col">역할</th><th scope="col">상태</th><th scope="col">부여일시</th><th scope="col">회수일시</th></tr></thead>
          <tbody>
            {roles.data.map((item) => (
              <tr key={item.employee_role_id}>
                <th scope="row">{roleLabel(master.roles, item.role_code)}</th>
                <td><Badge tone={item.revoked_at ? "neutral" : "success"}>{item.revoked_at ? "회수" : "활성"}</Badge></td>
                <td>{formatDateTime(item.assigned_at)}</td>
                <td>{formatDateTime(item.revoked_at)}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Card>
  )
}
