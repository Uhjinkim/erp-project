import { useState } from "react"
import type { FormEvent } from "react"
import { Button, Card, EmptyState, Select, Table, TextInput } from "../../../components/ui"
import type { VacationRequest, VacationType } from "../../../types/vacation"
import { availableActions, canResubmit, displayDateTime, filterRequests, statuses, typeName } from "../model"
import type { VacationHref } from "../navigation"
import { StatusBadge } from "./RequestSummary"
import styles from "../vacation.module.css"

export function RequestList({ items, types, employeeNo, isHRManager = false, search, screen, href, onRefresh }: {
  items: VacationRequest[]; types: VacationType[]; employeeNo: number; isHRManager?: boolean; search: string; screen: string; href: VacationHref; onRefresh: () => void
}) {
  const current = new URLSearchParams(search)
  const [filter, setFilter] = useState(() => Object.fromEntries(["status", "type", "q", "from", "to"].map((key) => [key, current.get(key) ?? ""])))
  const visible = filterRequests(items, search)
  const pageCount = Math.max(1, Math.ceil(visible.length / 10))
  const requestedPage = Number(current.get("page"))
  const page = Number.isSafeInteger(requestedPage) && requestedPage > 0 ? Math.min(pageCount, requestedPage) : 1
  const rows = visible.slice((page - 1) * 10, page * 10)
  const set = (key: string, value: string) => setFilter((previous) => ({ ...previous, [key]: value }))
  function apply(event: FormEvent) {
    event.preventDefault()
    const params = new URLSearchParams()
    for (const [key, value] of Object.entries(filter)) if (value) params.set(key, value)
    if (current.get("order")) params.set("order", current.get("order")!)
    window.location.hash = href(screen, undefined, params)
  }
  const pageHref = (next: number) => {
    const query = new URLSearchParams(search)
    query.set("page", String(next))
    return href(screen, undefined, query)
  }

  return <div className={styles.stack}>
    <div className={styles.metrics}>{["전체", "대기", "승인", "회수"].map((status) => <div key={status}><span>{status}</span><strong>{status === "전체" ? items.length : items.filter((item) => item.status === status).length}<small>건</small></strong></div>)}</div>
    <Card title="신청 검색" actions={<Button variant="ghost" size="small" onClick={onRefresh}>새로고침</Button>}>
      <form onSubmit={apply} className={styles.stack}>
        <div className={styles.filters}>
          <TextInput label="신청번호·신청자 사번" type="search" value={filter.q} onChange={(event) => set("q", event.target.value)} />
          <Select label="상태" value={filter.status} onChange={(event) => set("status", event.target.value)}><option value="">전체</option>{statuses.map((status) => <option key={status}>{status}</option>)}</Select>
          <Select label="휴가 유형" value={filter.type} onChange={(event) => set("type", event.target.value)}><option value="">전체</option>{types.map((type) => <option key={type.type_id} value={type.type_id}>{type.type_name}</option>)}</Select>
          <TextInput label="휴가 시작일 · 이후" type="date" value={filter.from} onChange={(event) => set("from", event.target.value)} />
          <TextInput label="휴가 시작일 · 이전" type="date" min={filter.from || undefined} value={filter.to} onChange={(event) => set("to", event.target.value)} />
        </div>
        <div className={styles.row}><Button type="submit">필터 적용</Button><a href={href(screen)}>모두 지우기</a>{screen === "leave-mine" && <a href={href("leave-apply")}>새 휴가 신청</a>}</div>
      </form>
    </Card>
    <Card title={`${screen === "leave-mine" || screen === "leave-resubmit" ? "내 신청" : "내 승인 대상"} · ${visible.length}건`}>
      {rows.length === 0 ? <EmptyState title={items.length ? "조건에 맞는 신청이 없습니다" : "표시할 신청이 없습니다"} /> : <Table caption="휴가 신청 목록">
        <thead><tr><th scope="col"><Button variant="ghost" size="small" onClick={() => { const query = new URLSearchParams(search)
          query.set("order", current.get("order") === "asc" ? "desc" : "asc")
          window.location.hash = href(screen, undefined, query)
        }}>신청번호 {current.get("order") === "asc" ? "↑" : "↓"}</Button></th><th scope="col">신청자</th><th scope="col">유형</th><th scope="col">사용 기간</th><th scope="col">일수</th><th scope="col">승인자</th><th scope="col">상태</th><th scope="col">작업</th></tr></thead>
        <tbody>{rows.map((item) => {
          const actions = availableActions(item, employeeNo, isHRManager)
          return <tr key={item.request_id}><td><a href={href("leave-detail", item.request_id)}>LV-{item.request_id}</a></td><td>{item.employee_no}</td><td>{typeName(item.type_id, types)}</td><td>{displayDateTime(item.start_datetime)}<br />{displayDateTime(item.end_datetime)}</td><td>{item.use_days}일</td><td>{item.approver_no ?? "인사 관리자 공용 승인"}</td><td><StatusBadge status={item.status} /></td><td><div className={styles.row}>
            <a href={href("leave-detail", item.request_id)}>상세</a>
            {actions.includes("cancel") && <a href={href("leave-detail", item.request_id)}>신청 취소</a>}
            {actions.includes("approve") && <a href={href("leave-approve", item.request_id)}>승인·반려</a>}
            {actions.includes("recall") && <a href={href("leave-recall", item.request_id)}>회수</a>}
            {canResubmit(item, employeeNo) && <a href={href("leave-resubmit", item.request_id)}>재신청</a>}
          </div></td></tr>
        })}</tbody>
      </Table>}
      {visible.length > 0 && <nav className={styles.pagination} aria-label="휴가 목록 페이지"><span>{(page - 1) * 10 + 1}–{Math.min(page * 10, visible.length)} / {visible.length}건 · {page}/{pageCount}페이지</span><div className={styles.row}>{page > 1 && <a href={pageHref(page - 1)}>이전 페이지</a>}{page < pageCount && <a href={pageHref(page + 1)}>다음 페이지</a>}</div></nav>}
    </Card>
  </div>
}
