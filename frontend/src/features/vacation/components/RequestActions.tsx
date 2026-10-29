import { useState } from "react"
import { changeVacationStatus } from "../../../api/vacation"
import { Alert, Button, Card, ConfirmDialog, Textarea } from "../../../components/ui"
import type { VacationAction, VacationRequest, VacationType } from "../../../types/vacation"
import { availableActions, canResubmit } from "../model"
import { useVacationMutation } from "../hooks"
import type { VacationHref } from "../navigation"
import { RequestSummary } from "./RequestSummary"
import styles from "../vacation.module.css"

const labels: Record<VacationAction, string> = { cancel: "신청 취소", approve: "승인", reject: "반려", recall: "승인 회수" }

export function RequestActions({ item, types, employeeNo, href, screen, onRefresh, onProcessed }: {
  item: VacationRequest; types: VacationType[]; employeeNo: number; href: VacationHref; screen: string; onRefresh: () => void; onProcessed: (item: VacationRequest) => void
}) {
  const mutation = useVacationMutation()
  const current = mutation.saved ?? item
  const [action, setAction] = useState<VacationAction | null>(null)
  const [reason, setReason] = useState("")
  const [reasonError, setReasonError] = useState("")
  const actions = availableActions(current, employeeNo).filter((value) => screen === "leave-approve" ? value === "approve" || value === "reject" : screen === "leave-recall" ? value === "recall" : true)
  const needsReason = action === "reject" || action === "recall"
  async function confirm() {
    if (!action || !actions.includes(action)) return
    if (needsReason && (!reason.trim() || reason.trim().length > 255)) {
      setReasonError("처리 사유를 1~255자로 입력하세요.")
      return
    }
    const saved = await mutation.execute(() => changeVacationStatus(employeeNo, item.request_id, action, reason))
    if (saved) { setAction(null); onProcessed(saved) }
  }
  return <div className={styles.stack}>
    {mutation.saved && <Alert tone="success">처리되었습니다. 현재 상태: {mutation.saved.status}</Alert>}
    <div className={screen === "leave-detail" ? styles.stack : styles.workspace}>
    <RequestSummary item={current} types={types} />
    <Card title="신청 처리">
      {actions.length === 0 && !canResubmit(current, employeeNo) && <Alert>현재 신청 상태와 담당자 기준으로 처리할 작업이 없습니다.</Alert>}
      <div className={styles.row}>{actions.map((value) => <Button key={value} variant={value === "approve" ? "primary" : "danger"} disabled={mutation.pending} onClick={() => { setReason(""); setReasonError(""); setAction(value) }}>{labels[value]}</Button>)}
        {canResubmit(current, employeeNo) && <a href={href("leave-resubmit", current.request_id)}>수정·재신청</a>}
        <a href={href("leave-detail", current.request_id)}>상세·이력</a><a href={href("leave-mine")}>내 신청</a><a href={href("leave-queue")}>승인 대기함</a>
        <Button variant="ghost" onClick={onRefresh} disabled={mutation.pending}>새로고침</Button>
      </div>
      {!action && mutation.error && <Alert tone="error">{mutation.error.message}</Alert>}
    </Card>
    </div>
    <ConfirmDialog open={action !== null} title={action ? `LV-${current.request_id} ${labels[action]}` : "신청 처리"} busy={mutation.pending} onClose={() => setAction(null)} onConfirm={() => void confirm()} confirmLabel={action ? labels[action] : "확인"} danger={action !== "approve"}>
      <div className={styles.stack}>
        <p>{action === "approve" ? "이 신청을 승인합니다." : action === "cancel" ? "대기 중인 본인 신청을 취소합니다." : action === "recall" ? "승인을 회수합니다. 신청자는 수정 후 다시 신청할 수 있습니다." : "이 신청을 반려합니다."}</p>
        {needsReason && <Textarea label="처리 사유" required maxLength={255} rows={4} value={reason} error={reasonError} disabled={mutation.pending} onChange={(event) => { setReason(event.target.value); setReasonError("") }} />}
        {mutation.error && <Alert tone="error">{mutation.error.message}</Alert>}
      </div>
    </ConfirmDialog>
  </div>
}
