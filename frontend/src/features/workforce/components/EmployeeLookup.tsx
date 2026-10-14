import { useCallback, useState } from "react"
import type { FormEvent } from "react"
import { Badge, Button, Card, EmptyState, Table, TextInput } from "../../../components/ui"
import { useWorkforceQuery } from "../hooks"
import { pageOf, tenureTone } from "../model"
import styles from "../workforce.module.css"
import { Pager } from "./Pager"
import { QueryFallback } from "./QueryFallback"

export type LookupRow = {
  emp_no: number
  name: string
  organization: string
  status: string
  dates: string
}

type EmployeeLookupProps = {
  title: string
  description: string
  enabled: boolean
  load: (keyword: string) => Promise<LookupRow[]>
  hrefFor: (row: LookupRow) => string
  actionLabel: string
}

// 처리 대상 사원을 고르는 모듈 내부 검색 목록. 검색 조건은 서버 조회로 전달한다.
export function EmployeeLookup({ title, description, enabled, load, hrefFor, actionLabel }: EmployeeLookupProps) {
  const [draft, setDraft] = useState("")
  const [keyword, setKeyword] = useState("")
  const [page, setPage] = useState(1)
  const loader = useCallback(() => load(keyword), [load, keyword])
  const query = useWorkforceQuery(enabled, loader)

  function submit(event: FormEvent) {
    event.preventDefault()
    setKeyword(draft.trim())
    setPage(1)
  }

  const rows = query.data ?? []
  const current = pageOf(rows, page)
  return (
    <Card title={title}>
      <p className={styles.hint}>{description}</p>
      <form className={styles.row} role="search" onSubmit={submit}>
        <TextInput label="이름 또는 사번" value={draft} onChange={(event) => setDraft(event.target.value)} />
        <Button type="submit" variant="secondary" pending={query.loading}>검색</Button>
      </form>
      <QueryFallback query={query} label="사원을 찾는 중" />
      {query.data && query.error && <p className={styles.hint} role="alert">{query.error}</p>}
      {query.data && rows.length === 0 && <EmptyState title="조건에 맞는 사원이 없습니다" />}
      {rows.length > 0 && (
        <>
          <Table caption={`${title} 검색 결과`}>
            <thead><tr><th scope="col">사번</th><th scope="col">이름</th><th scope="col">부서·직급</th><th scope="col">상태</th><th scope="col">기간</th><th scope="col"><span className={styles.subtext}>작업</span></th></tr></thead>
            <tbody>
              {current.items.map((row) => (
                <tr key={row.emp_no}>
                  <td>{row.emp_no}</td>
                  <th scope="row">{row.name}</th>
                  <td>{row.organization}</td>
                  <td><Badge tone={tenureTone(row.status)}>{row.status}</Badge></td>
                  <td className={styles.nowrap}>{row.dates}</td>
                  <td><a href={hrefFor(row)} aria-label={`${row.name} ${actionLabel}`}>{actionLabel}</a></td>
                </tr>
              ))}
            </tbody>
          </Table>
          <Pager page={current.page} pages={current.pages} total={rows.length} onChange={setPage} />
        </>
      )}
    </Card>
  )
}
