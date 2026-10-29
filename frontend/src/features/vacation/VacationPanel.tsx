import { useState } from "react"
import { Alert, EmptyState, ErrorState, Select, Spinner } from "../../components/ui"
import { environment } from "../../config/environment"
import type { CurrentUser } from "../../types/auth"
import { useVacationData } from "./hooks"
import { failureTitle } from "./data"
import { canResubmit, requestIdFromSearch } from "./model"
import { vacationNavigation } from "./navigation"
import { RequestForm } from "./components/RequestForm"
import { RequestList } from "./components/RequestList"
import { RequestActions } from "./components/RequestActions"
import { RequestHistory } from "./components/RequestHistory"
import styles from "./vacation.module.css"

const employees = [1001, 1002, 2001, 9001]

export function VacationPanel({ currentUser, screenId, search = "" }: { currentUser: CurrentUser | null; screenId: string; search?: string }) {
  const query = new URLSearchParams(search)
  const development = environment.authMode === "development"
  const candidate = Number(query.get("employeeNo"))
  const identity = development ? employees.includes(candidate) ? candidate : 1001 : currentUser?.employee?.emp_no ?? 0
  return <div className={styles.stack}>
    {development && <Select label="개발용 현재 사용자" value={identity} onChange={(event) => { window.location.hash = vacationNavigation(Number(event.target.value))(screenId, undefined, query) }}>{employees.map((no) => <option key={no} value={no}>{no} · {no === 2001 ? "승인자" : no === 9001 ? "인사관리자" : "신청자"}</option>)}</Select>}
    {!identity ? <EmptyState title="연결된 사원 정보가 없습니다">사원 연결을 확인한 후 다시 로그인하세요.</EmptyState> : <VacationWorkspace key={`${identity}:${screenId}`} employeeNo={identity} screen={screenId} search={search} development={development} />}
  </div>
}

function VacationWorkspace({ employeeNo, screen, search, development }: { employeeNo: number; screen: string; search: string; development: boolean }) {
  const [notice, setNotice] = useState<{ id: number; message: string } | null>(null)
  const requestId = requestIdFromSearch(search)
  const data = useVacationData(employeeNo, true, screen, requestId)
  const href = vacationNavigation(development ? employeeNo : undefined)
  const retry = (error: Error) => <ErrorState title={failureTitle(error)} onRetry={data.refresh}>{error.message}</ErrorState>
  const links = <div className={styles.row}><a href={href("leave-apply")}>휴가 신청</a><a href={href("leave-mine")}>내 신청</a><a href={href("leave-queue")}>승인 대기함</a></div>
  if (data.loading) return <Spinner label="휴가 정보를 불러오는 중" />
  if (new URLSearchParams(search).has("requestId") && !requestId) return <EmptyState title="신청번호가 올바르지 않습니다" action={links}>목록에서 신청을 선택하세요.</EmptyState>
  const item = [...data.mine, ...data.approvals].find((row) => row.request_id === requestId)
  const source = screen === "leave-mine" || screen === "leave-resubmit" ? "mine" : "approvals"
  let content
  if (screen === "leave-apply") content = data.errors.types ? retry(data.errors.types) : data.types.length ? <RequestForm employeeNo={employeeNo} types={data.types} href={href} /> : <EmptyState title="등록된 휴가 유형이 없습니다" />
  else if (screen === "leave-detail") content = !requestId ? <EmptyState title="상세를 볼 신청을 선택하세요" action={links} /> : <div className={styles.stack}>
    <div className={styles.workspace}><div className={styles.stack}>
    {item ? <RequestActions key={`${item.request_id}:${JSON.stringify(item)}`} item={item} types={data.types} employeeNo={employeeNo} href={href} screen={screen} onRefresh={data.refresh} onProcessed={(saved) => { setNotice({ id: saved.request_id, message: `처리되었습니다. 현재 상태: ${saved.status}` }); data.refresh() }} /> : <Alert tone="warning">내 신청·승인 대상 목록에서 현재 신청 정보를 조회하지 못했습니다. 조회 권한이 있는 변경 이력은 아래에서 확인할 수 있습니다.</Alert>}
    {data.errors.mine && retry(data.errors.mine)}{data.errors.approvals && retry(data.errors.approvals)}</div>
    {data.errors.history ? retry(data.errors.history) : <RequestHistory history={data.history} types={data.types} />}</div>{links}
  </div>
  else if (data.errors[source]) content = retry(data.errors[source])
  else if (requestId && !item) content = <EmptyState title="이 목록에서 신청을 찾을 수 없습니다" action={links}>담당자와 신청번호를 확인하거나 목록을 새로 조회하세요.</EmptyState>
  else if (requestId && item && screen === "leave-resubmit") content = canResubmit(item, employeeNo) ? data.errors.types ? retry(data.errors.types) : <RequestForm key={item.request_id} initial={item} types={data.types} employeeNo={employeeNo} href={href} /> : <EmptyState title="회수된 본인 신청만 재신청할 수 있습니다" action={links} />
  else if (requestId && item) content = <RequestActions key={`${item.request_id}:${JSON.stringify(item)}`} item={item} types={data.types} employeeNo={employeeNo} href={href} screen={screen} onRefresh={data.refresh} onProcessed={(saved) => { setNotice({ id: saved.request_id, message: `처리되었습니다. 현재 상태: ${saved.status}` }); data.refresh() }} />
  else {
    const items = data[source].filter((row) => screen === "leave-resubmit" ? canResubmit(row, employeeNo) : screen === "leave-recall" ? row.status === "승인" : screen === "leave-approve" ? row.status === "대기" : true)
    content = <RequestList key={search} items={items} types={data.types} employeeNo={employeeNo} href={href} screen={screen} search={search} onRefresh={data.refresh} />
  }
  return <div className={styles.stack}>{notice?.id === requestId && <Alert tone="success">{notice.message}</Alert>}{data.errors.types && screen !== "leave-apply" && <Alert tone="warning">휴가 유형 이름을 불러오지 못했습니다. 유형 코드로 표시합니다.</Alert>}{content}</div>
}
