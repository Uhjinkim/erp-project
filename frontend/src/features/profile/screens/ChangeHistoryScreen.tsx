import { useState } from "react"
import { listChangeRequests, processChangeRequest } from "../../../api/profile"
import { Alert, Badge, Button, Card, ConfirmDialog, EmptyState, Select, Table } from "../../../components/ui"
import type { PersonalInfoChangeRequest } from "../../../types/profile"
import { ChangeList } from "../components/ChangeValues"
import { QueryFallback } from "../components/QueryFallback"
import { useMutation, useProfileQuery } from "../hooks"
import { CHANGE_STATUSES, formatDateTime, navigate, parseStatus, profileHref, statusTone } from "../model"
import styles from "../profile.module.css"

const savedMessages: Record<string, string> = { request: "변경 요청을 제출했습니다. 승인되면 반영됩니다." }

// FN-HR-005 내 요청 이력, FN-HR-011 대기 요청 취소. Query keys: status, saved.
export function ChangeHistoryScreen({ enabled, search, onChanged }: { enabled: boolean; search: URLSearchParams; onChanged: () => void }) {
  const status = parseStatus(search.get("status"))
  // 화면은 URL마다 다시 마운트되므로 조회 조건은 마운트 시점 값으로 고정한다.
  const [loader] = useState(() => () => listChangeRequests({ mine: true, status }))
  const query = useProfileQuery(enabled, loader)
  const [target, setTarget] = useState<PersonalInfoChangeRequest | null>(null)
  const [notice, setNotice] = useState(savedMessages[search.get("saved") ?? ""] ?? "")
  const mutation = useMutation()

  async function cancel() {
    if (!target) return
    const result = await mutation.run(() => processChangeRequest(target.request_id, "cancel"))
    if (result) {
      setTarget(null)
      setNotice("변경 요청을 취소했습니다.")
      onChanged()
      void query.reload()
    }
  }

  const rows = query.data ? [...query.data].sort((a, b) => b.requested_at.localeCompare(a.requested_at)) : []
  return (
    <Card title="내 변경 요청 이력" actions={<Button size="small" variant="secondary" pending={query.loading} onClick={() => void query.reload()}>새로고침</Button>}>
      {notice && <Alert tone="success">{notice}</Alert>}
      <div className={styles.filters}>
        <Select label="상태" value={status ?? ""} onChange={(event) => navigate(profileHref("change-history", { status: event.target.value }))}>
          <option value="">전체</option>
          {CHANGE_STATUSES.map((item) => <option key={item} value={item}>{item}</option>)}
        </Select>
        <Button variant="ghost" onClick={() => navigate(profileHref("change-request"))}>새 변경 요청</Button>
      </div>
      <QueryFallback query={query} label="요청 이력을 불러오는 중" />
      {query.data && query.error && <p className={styles.hint} role="alert">{query.error}</p>}
      {query.data && rows.length === 0 && <EmptyState title={status ? `${status} 상태의 요청이 없습니다` : "변경 요청 이력이 없습니다"} />}
      {rows.length > 0 && (
        <Table caption="내 개인정보 변경 요청">
          <thead><tr><th scope="col">요청일시</th><th scope="col">상태</th><th scope="col">변경 내용</th><th scope="col">처리 결과</th><th scope="col">작업</th></tr></thead>
          <tbody>
            {rows.map((request) => (
              <tr key={request.request_id}>
                <th scope="row" className={styles.nowrap}>{formatDateTime(request.requested_at)}</th>
                <td><Badge tone={statusTone(request.status)}>{request.status}</Badge></td>
                <td><ChangeList request={request} /></td>
                <td>
                  {request.processed_at ? formatDateTime(request.processed_at) : "-"}
                  {request.reject_reason && <span className={styles.subtext}>반려 사유: {request.reject_reason}</span>}
                </td>
                <td>{request.status === "대기"
                  ? <Button size="small" variant="danger" onClick={() => { mutation.reset(); setTarget(request) }}>요청 취소</Button>
                  : <span className={styles.subtext}>-</span>}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
      <ConfirmDialog open={target !== null} danger title="변경 요청 취소" confirmLabel="요청 취소" busy={mutation.pending} onClose={() => setTarget(null)} onConfirm={() => void cancel()}>
        <p>대기 중인 변경 요청을 취소합니다. 취소한 요청은 되돌릴 수 없고 이력에 남습니다.</p>
        {mutation.error && <Alert tone="error">{mutation.error}</Alert>}
      </ConfirmDialog>
    </Card>
  )
}
