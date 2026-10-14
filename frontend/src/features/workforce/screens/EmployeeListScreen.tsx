import { useState } from "react"
import type { FormEvent } from "react"
import { listEmployees, listRetiredEmployees } from "../../../api/workforce"
import { Badge, Button, Card, EmptyState, Select, Table, Tabs, TextInput } from "../../../components/ui"
import { Pager } from "../components/Pager"
import { QueryFallback } from "../components/QueryFallback"
import type { MasterData } from "../hooks"
import { useWorkforceQuery } from "../hooks"
import { TENURE_STATUSES, departmentLabel, pageOf, parseId, positionLabel, tenureTone, workforceHref } from "../model"
import styles from "../workforce.module.css"

type ListProps = { enabled: boolean; search: URLSearchParams; master: MasterData }

const views = [{ value: "employees", label: "사원 목록" }, { value: "retired", label: "퇴사자 조회" }]

// Query keys: view=employees|retired, q, dept, status, page (사원) / name, dept, empNo, from, to, page (퇴사자).
export function EmployeeListScreen({ enabled, search, master }: ListProps) {
  const view = search.get("view") === "retired" ? "retired" : "employees"
  return (
    <div className={styles.stack}>
      <div className={styles.spread}>
        <p className={styles.hint}>인사관리자 전용 조회입니다(HR-001, HR-005). 검색 조건은 서버 조회에 그대로 전달합니다.</p>
        <a href={workforceHref("employee-create")}>신규 사원 등록</a>
      </div>
      <Tabs label="사원 조회 구분" items={views} value={view} onChange={(value) => { window.location.hash = workforceHref("employee-list", { view: value === "retired" ? "retired" : undefined }) }}>
        {view === "retired"
          ? <RetiredList enabled={enabled} search={search} master={master} />
          : <ActiveList enabled={enabled} search={search} master={master} />}
      </Tabs>
    </div>
  )
}

function ActiveList({ enabled, search, master }: ListProps) {
  const filters = { search: search.get("q") ?? "", dept_no: search.get("dept") ?? "", tenure_status: search.get("status") ?? "" }
  const [draft, setDraft] = useState(filters)
  // 화면은 URL마다 다시 마운트되므로 조회 조건은 마운트 시점 값으로 고정한다.
  const [loader] = useState(() => () => listEmployees(filters))
  const query = useWorkforceQuery(enabled, loader)
  const page = parseId(search.get("page")) ?? 1

  function submit(event: FormEvent) {
    event.preventDefault()
    window.location.hash = workforceHref("employee-list", { q: draft.search.trim(), dept: draft.dept_no, status: draft.tenure_status })
  }
  const goToPage = (next: number) => { window.location.hash = workforceHref("employee-list", { q: filters.search, dept: filters.dept_no, status: filters.tenure_status, page: next }) }

  const rows = query.data ?? []
  const current = pageOf(rows, page)
  return (
    <Card title="사원 목록" actions={<Button variant="secondary" size="small" pending={query.loading} onClick={() => void query.reload()}>새로고침</Button>}>
      <form className={styles.filterGrid} role="search" onSubmit={submit}>
        <TextInput label="이름·이메일·사번" value={draft.search} onChange={(event) => setDraft({ ...draft, search: event.target.value })} />
        <Select label="부서" value={draft.dept_no} onChange={(event) => setDraft({ ...draft, dept_no: event.target.value })}>
          <option value="">전체</option>
          {master.departments.map((item) => <option key={item.dept_no} value={item.dept_no}>{item.dept_name}</option>)}
        </Select>
        <Select label="재직 상태" value={draft.tenure_status} onChange={(event) => setDraft({ ...draft, tenure_status: event.target.value })}>
          <option value="">전체</option>
          {TENURE_STATUSES.map((status) => <option key={status} value={status}>{status}</option>)}
        </Select>
        <Button type="submit">검색</Button>
      </form>
      <QueryFallback query={query} label="사원 목록을 불러오는 중" />
      {query.data && query.error && <p className={styles.hint} role="alert">{query.error}</p>}
      {query.data && rows.length === 0 && <EmptyState title="조건에 맞는 사원이 없습니다" action={<a href={workforceHref("employee-list")}>조건 초기화</a>} />}
      {rows.length > 0 && (
        <>
          <Table caption="사원 목록">
            <thead><tr><th scope="col">사번</th><th scope="col">이름</th><th scope="col">부서</th><th scope="col">직급</th><th scope="col">재직 상태</th><th scope="col">사내 이메일</th><th scope="col">입사일</th></tr></thead>
            <tbody>
              {current.items.map((employee) => (
                <tr key={employee.emp_no}>
                  <td>{employee.emp_no}</td>
                  <th scope="row"><a href={workforceHref("employee-detail", { empNo: employee.emp_no })}>{employee.name}</a></th>
                  <td>{departmentLabel(master.departments, employee.dept_no)}</td>
                  <td>{positionLabel(master.positions, employee.position_code)}</td>
                  <td><Badge tone={tenureTone(employee.tenure_status)}>{employee.tenure_status}</Badge></td>
                  <td className={styles.wrap}>{employee.email ?? "미등록"}</td>
                  <td className={styles.nowrap}>{employee.hire_date}</td>
                </tr>
              ))}
            </tbody>
          </Table>
          <Pager page={current.page} pages={current.pages} total={rows.length} onChange={goToPage} />
        </>
      )}
    </Card>
  )
}

function RetiredList({ enabled, search, master }: ListProps) {
  const filters = {
    name: search.get("name") ?? "", dept_no: search.get("dept") ?? "", emp_no: search.get("empNo") ?? "",
    term_date_from: search.get("from") ?? "", term_date_to: search.get("to") ?? "",
  }
  const [draft, setDraft] = useState(filters)
  const [loader] = useState(() => () => listRetiredEmployees(filters))
  const query = useWorkforceQuery(enabled, loader)
  const page = parseId(search.get("page")) ?? 1
  const params = (values: typeof filters, next?: number) => ({
    view: "retired", name: values.name.trim(), dept: values.dept_no, empNo: values.emp_no.trim(),
    from: values.term_date_from, to: values.term_date_to, page: next,
  })

  function submit(event: FormEvent) {
    event.preventDefault()
    window.location.hash = workforceHref("employee-list", params(draft))
  }

  const rows = query.data ?? []
  const current = pageOf(rows, page)
  return (
    <Card title="퇴사자 조회" actions={<Button variant="secondary" size="small" pending={query.loading} onClick={() => void query.reload()}>새로고침</Button>}>
      <form className={styles.filterGrid} role="search" onSubmit={submit}>
        <TextInput label="이름" value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} />
        <TextInput label="사번" inputMode="numeric" pattern="\d*" value={draft.emp_no} onChange={(event) => setDraft({ ...draft, emp_no: event.target.value })} />
        <Select label="퇴사 당시 부서" value={draft.dept_no} onChange={(event) => setDraft({ ...draft, dept_no: event.target.value })}>
          <option value="">전체</option>
          {master.departments.map((item) => <option key={item.dept_no} value={item.dept_no}>{item.dept_name}</option>)}
        </Select>
        <span />
        <TextInput label="퇴사일 시작" type="date" value={draft.term_date_from} onChange={(event) => setDraft({ ...draft, term_date_from: event.target.value })} />
        <TextInput label="퇴사일 종료" type="date" value={draft.term_date_to} onChange={(event) => setDraft({ ...draft, term_date_to: event.target.value })} />
        <Button type="submit">검색</Button>
      </form>
      <QueryFallback query={query} label="퇴사자를 불러오는 중" />
      {query.data && query.error && <p className={styles.hint} role="alert">{query.error}</p>}
      {query.data && rows.length === 0 && <EmptyState title="조건에 맞는 퇴사자가 없습니다" />}
      {rows.length > 0 && (
        <>
          <Table caption="퇴사자 목록">
            <thead><tr><th scope="col">사번</th><th scope="col">이름</th><th scope="col">부서·직급</th><th scope="col">입사일</th><th scope="col">퇴사일</th><th scope="col">작업</th></tr></thead>
            <tbody>
              {current.items.map((employee) => (
                <tr key={employee.emp_no}>
                  <td>{employee.emp_no}</td>
                  <th scope="row"><a href={workforceHref("employee-detail", { empNo: employee.emp_no })}>{employee.name}</a></th>
                  <td>{employee.dept_name ?? "미배정"} · {employee.position_name ?? "미배정"}</td>
                  <td className={styles.nowrap}>{employee.hire_date}</td>
                  <td className={styles.nowrap}>{employee.term_date}</td>
                  <td><a href={workforceHref("rehire", { empNo: employee.emp_no })} aria-label={`${employee.name} 재입사 처리`}>재입사</a></td>
                </tr>
              ))}
            </tbody>
          </Table>
          <Pager page={current.page} pages={current.pages} total={rows.length} onChange={(next) => { window.location.hash = workforceHref("employee-list", params(filters, next)) }} />
        </>
      )}
    </Card>
  )
}
