import { Card, EmptyState, Table } from "../../../components/ui"
import type { VacationHistory, VacationType } from "../../../types/vacation"
import { displayDateTime, snapshotChanges } from "../model"
import styles from "../vacation.module.css"

export function RequestHistory({ history, types }: { history: VacationHistory[]; types: VacationType[] }) {
  const entries = [...history].sort((a, b) => a.changed_at.localeCompare(b.changed_at) || a.history_id - b.history_id)
  return <Card title="변경 이력">{entries.length === 0 ? <EmptyState title="기록된 변경 이력이 없습니다" /> : <ol className={styles.timeline}>{entries.map((entry) => {
    const changes = snapshotChanges(entry, types)
    return <li key={entry.history_id}>
      <strong>{entry.from_status ?? "신규"} → {entry.to_status}</strong>
      <p className={styles.hint}>{displayDateTime(entry.changed_at)} · 처리자 {entry.actor_employee_no}</p>
      {entry.reason && <p className={styles.reason}>{entry.reason}</p>}
      {changes === null ? <p className={styles.hint}>이 기록에는 비교할 전후 값이 없습니다.</p> : changes.length === 0 ? <p className={styles.hint}>신청 항목 변경 없음</p> : <Table caption={`이력 ${entry.history_id} 변경 항목`}><thead><tr><th scope="col">항목</th><th scope="col">변경 전</th><th scope="col">변경 후</th></tr></thead><tbody>{changes.map((change) => <tr key={change.key}><th scope="row">{change.label}</th><td>{change.before}</td><td>{change.after}</td></tr>)}</tbody></Table>}
    </li>
  })}</ol>}</Card>
}
