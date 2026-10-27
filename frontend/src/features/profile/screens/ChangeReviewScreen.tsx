import { useCallback, useState } from "react"
import { getChangeRequest, processChangeRequest } from "../../../api/profile"
import { Alert, Badge, Button, Card, ConfirmDialog, DetailList, EmptyState, Textarea } from "../../../components/ui"
import type { PersonalInfoChangeRequest } from "../../../types/profile"
import { ChangeComparison } from "../components/ChangeValues"
import { QueryFallback } from "../components/QueryFallback"
import { useMutation, useProfileQuery } from "../hooks"
import { firstFieldErrors, formatDateTime, navigate, parseId, profileHref, statusTone } from "../model"
import styles from "../profile.module.css"

// FN-HR-004 승인·반려. Query key: requestId(필수). 처리 가능 여부는 서버 응답의 can_process를 따른다.
export function ChangeReviewScreen({ enabled, search }: { enabled: boolean; search: URLSearchParams }) {
  const requestId = parseId(search.get("requestId"))
  if (requestId === null) {
    return <EmptyState title="처리할 요청을 선택하세요" action={<a href={profileHref("change-queue")}>처리함으로 이동</a>}>처리 화면 주소에는 요청 번호(requestId)가 필요합니다.</EmptyState>
  }
  return <ReviewView requestId={requestId} enabled={enabled} />
}

function ReviewView({ requestId, enabled }: { requestId: number; enabled: boolean }) {
  const load = useCallback(() => getChangeRequest(requestId), [requestId])
  const query = useProfileQuery(enabled, load)
  if (!query.data) return <QueryFallback query={query} label="요청을 불러오는 중" />
  return <ReviewForm request={query.data} onStale={() => void query.reload()} />
}

function ReviewForm({ request, onStale }: { request: PersonalInfoChangeRequest; onStale: () => void }) {
  const [action, setAction] = useState<"approve" | "reject" | null>(null)
  const [reason, setReason] = useState("")
  const mutation = useMutation()
  const processable = request.status === "대기" && request.can_process

  async function confirm() {
    if (!action) return
    const result = await mutation.run(() => processChangeRequest(request.request_id, action, action === "reject" ? reason.trim() || undefined : undefined))
    if (result) {
      navigate(profileHref("change-queue", { saved: action === "approve" ? "approved" : "rejected" }))
    } else {
      setAction(null)
      onStale()
    }
  }

  return (
    <div className={styles.stack}>
      <Card title={`수정 요청 #${request.request_id}`} actions={<a href={profileHref("change-queue")}>처리함</a>}>
        <DetailList items={[
          { key: "emp", label: "요청자 사번", value: request.emp_no },
          { key: "status", label: "상태", value: <Badge tone={statusTone(request.status)}>{request.status}</Badge> },
          { key: "requested", label: "요청일시", value: formatDateTime(request.requested_at) },
          ...(request.processed_at ? [{ key: "processed", label: "처리일시", value: `${formatDateTime(request.processed_at)} (처리자 ${request.processed_by ?? "-"})` }] : []),
          ...(request.reject_reason ? [{ key: "reason", label: "반려 사유", value: request.reject_reason }] : []),
        ]} />
      </Card>
      <Card title="변경 전·후 비교">
        <ChangeComparison request={request} revealAccount={processable} />
        {processable && <p className={styles.hint}>승인하면 요청 값이 인사정보에 바로 반영됩니다. 현재 계좌는 가려서 표시합니다.</p>}
      </Card>
      {mutation.error && <Alert tone="error" title="처리하지 못했습니다">{mutation.error} 최신 상태를 다시 불러왔습니다.</Alert>}
      {processable
        ? <Card title="처리">
            <div className={styles.stack}>
              <Textarea label="반려 사유 (선택)" maxLength={500} rows={3} value={reason} error={firstFieldErrors(mutation.fieldErrors).reason} hint="반려할 때 요청자에게 표시됩니다." onChange={(event) => setReason(event.target.value)} />
              <div className={styles.formFooter}>
                <Button variant="danger" onClick={() => { mutation.reset(); setAction("reject") }}>반려</Button>
                <Button onClick={() => { mutation.reset(); setAction("approve") }}>승인</Button>
              </div>
            </div>
          </Card>
        : <Alert tone="info">{request.status === "대기" ? "이 요청을 처리할 권한이 없습니다." : "이미 처리가 끝난 요청입니다."}</Alert>}
      <ConfirmDialog open={action !== null} danger={action === "reject"} title={action === "approve" ? "개인정보 변경 승인" : "개인정보 변경 반려"}
        confirmLabel={action === "approve" ? "승인" : "반려"} busy={mutation.pending} onClose={() => setAction(null)} onConfirm={() => void confirm()}>
        <p>{action === "approve" ? `사번 ${request.emp_no}의 요청 값을 인사정보에 반영합니다.` : `사번 ${request.emp_no}의 요청을 반려합니다. 기존 값은 유지됩니다.`}</p>
        {action === "reject" && <p className={styles.hint}>반려 사유: {reason.trim() || "입력하지 않음"}</p>}
      </ConfirmDialog>
    </div>
  )
}
