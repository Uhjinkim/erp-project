import { Badge, Card, DetailList } from "../../../components/ui"
import type { VacationRequest, VacationStatus, VacationType } from "../../../types/vacation"
import { displayDateTime, typeName } from "../model"
import styles from "../vacation.module.css"

export function StatusBadge({ status }: { status: VacationStatus }) {
  return <Badge tone={status === "승인" ? "success" : status === "반려" ? "error" : status === "대기" || status === "회수" ? "warning" : "neutral"}>{status}</Badge>
}

export function RequestSummary({ item, types }: { item: VacationRequest; types: VacationType[] }) {
  return <Card title={`신청 LV-${item.request_id}`}>
    <DetailList items={[
      { key: "employee", label: "신청자 사번", value: item.employee_no },
      { key: "type", label: "휴가 유형", value: typeName(item.type_id, types) },
      { key: "start", label: "시작 일시", value: displayDateTime(item.start_datetime) },
      { key: "end", label: "종료 일시", value: displayDateTime(item.end_datetime) },
      { key: "days", label: "사용 일수", value: `${item.use_days}일` },
      { key: "approver", label: "승인자 사번", value: item.approver_no },
      { key: "status", label: "현재 상태", value: <StatusBadge status={item.status} /> },
      { key: "approved", label: "승인 일시", value: displayDateTime(item.approved_at) },
    ]} />
    <p className={styles.text}>신청 사유 · {item.request_reason || "입력하지 않음"}</p>
    {item.reject_reason && <p className={styles.text}>반려 사유 · {item.reject_reason}</p>}
  </Card>
}
