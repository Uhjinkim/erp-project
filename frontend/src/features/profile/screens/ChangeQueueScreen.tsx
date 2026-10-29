import { useState } from "react"
import { listChangeRequests } from "../../../api/profile"
import { Alert, Button, Card, EmptyState, Table } from "../../../components/ui"
import { ChangeList } from "../components/ChangeValues"
import { QueryFallback } from "../components/QueryFallback"
import { useProfileQuery } from "../hooks"
import { formatDateTime, profileHref } from "../model"
import styles from "../profile.module.css"

const savedMessages: Record<string, string> = { approved: "수정 요청을 승인했습니다.", rejected: "수정 요청을 반려했습니다." }

// FN-HR-004 처리함. 서버가 현재 사용자가 처리할 수 있는 대기 요청만 반환한다(처리자 판정은 승인 시점 조직 기준).
export function ChangeQueueScreen({ enabled, search }: { enabled: boolean; search: URLSearchParams }) {
  const [loader] = useState(() => () => listChangeRequests({ processable: true }))
  const query = useProfileQuery(enabled, loader)
  const saved = savedMessages[search.get("saved") ?? ""]
  const rows = query.data ? [...query.data].sort((a, b) => a.requested_at.localeCompare(b.requested_at)) : []
  return (
    <Card title="처리 대기 요청" actions={<Button size="small" variant="secondary" pending={query.loading} onClick={() => void query.reload()}>새로고침</Button>}>
      {saved && <Alert tone="success">{saved}</Alert>}
      <p className={styles.hint}>오래된 요청부터 표시합니다. 목록의 계좌번호는 가려서 표시하며 처리 화면에서 확인할 수 있습니다.</p>
      <QueryFallback query={query} label="처리 대기 요청을 불러오는 중" />
      {query.data && query.error && <p className={styles.hint} role="alert">{query.error}</p>}
      {query.data && rows.length === 0 && <EmptyState title="처리할 수정 요청이 없습니다" />}
      {rows.length > 0 && (
        <Table caption="처리 대기 중인 개인정보 수정 요청">
          <thead><tr><th scope="col">요청일시</th><th scope="col">사번</th><th scope="col">수정 내용</th><th scope="col">작업</th></tr></thead>
          <tbody>
            {rows.map((request) => (
              <tr key={request.request_id}>
                <th scope="row" className={styles.nowrap}>{formatDateTime(request.requested_at)}</th>
                <td>{request.emp_no}</td>
                <td><ChangeList request={request} /></td>
                <td><a href={profileHref("change-review", { requestId: request.request_id })} aria-label={`사번 ${request.emp_no} 요청 처리`}>처리</a></td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Card>
  )
}
