import { Card } from "../../../components/ui"
import type { EvaluationHistoryEntry } from "../../../types/evaluation"
import { ACTION_LABELS, formatDateTime } from "../model"
import styles from "../evaluation.module.css"

/** Shown only to the current evaluator and HR; the backend returns 403 to anyone else. */
export function EvaluationHistory({ entries }: { entries: EvaluationHistoryEntry[] }) {
  if (entries.length === 0) return null
  return <Card title="처리 이력">
    <ol className={styles.history}>
      {entries.map((entry) => <li key={entry.history_id}>
        <strong>{ACTION_LABELS[entry.action]}</strong>
        <small>{entry.actor_name ?? entry.actor_no} · {formatDateTime(entry.changed_at)}</small>
        {entry.action === "REASSIGN" && <small>평가자 {entry.from_evaluator_no} → {entry.to_evaluator_no}</small>}
        {entry.reason && <small>사유: {entry.reason}</small>}
      </li>)}
    </ol>
  </Card>
}
